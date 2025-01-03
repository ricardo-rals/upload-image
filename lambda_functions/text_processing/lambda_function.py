import json
import re
import nltk
nltk.data.path.append('/opt/python/nltk_data')
from difflib import SequenceMatcher
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from validate_docbr import CPF, CNPJ
import boto3

s3 = boto3.client('s3')

def clean_tokens(text, stop_words):
    """Tokeniza e remove stopwords do texto."""
    tokens = word_tokenize(text)
    return [word.lower() for word in tokens if word.lower() not in stop_words and word.isalnum()]

def match_percentage(word, target):
    """Calcula a similaridade entre duas palavras."""
    return SequenceMatcher(None, word.lower(), target.lower()).ratio()

def validate_cnpj(cnpj):
    """Valida e mascara um CNPJ."""
    cnpj_validator = CNPJ()
    if cnpj_validator.validate(cnpj):
        return cnpj_validator.mask(cnpj)
    return None

def validate_cpf(cpf):
    """Valida e mascara um CPF."""
    cpf_validator = CPF()
    if cpf_validator.validate(cpf):
        return cpf_validator.mask(cpf)
    return None

def update_confidence(confidence_dict, field_name, value, confidence):
    """Atualiza o dicionário de confiança com base no valor e na confiança."""
    if field_name not in confidence_dict or confidence > confidence_dict[field_name]["confidence"]:
        confidence_dict[field_name] = {"value": value, "confidence": confidence}

def clean_value(value):
    """Limpa valores específicos de CNPJ/CPF, removendo caracteres indesejados como &."""
    cleaned_value = re.sub(r'\D', '', value)  # Remove outros caracteres não numéricos
    return cleaned_value

# Função principal de extração de informações

def extract_information(textract_data):
    stop_words = set(stopwords.words('portuguese'))  # Carrega as stopwords em português
    extracted_info = {
        "nome_emissor": None,
        "CNPJ_emissor": None,
        "endereco_emissor": None,
        "CNPJ_CPF_consumidor": None,
        "data_emissao": None,
        "numero_nota_fiscal": None,
        "serie_nota_fiscal": None,
        "valor_total": None,
        "forma_pgto": "outros"
    }
    confidence_dict = {}
    similarity_threshold = 0.7

    for document in textract_data.get("ExpenseDocuments", []):
        # Array para armazenar valores não nulos e não vazios
        non_empty_values = []

        for field in document.get("SummaryFields", []):
            value = field.get("ValueDetection", {}).get("Text", "").strip()
            label = field.get("LabelDetection", {}).get("Text", "").strip()
            field_type = field.get("Type", {}).get("Text", "").upper()
            confidence = field.get("Type", {}).get("Confidence", 0)

            value_tokens = clean_tokens(value, stop_words)
            label_tokens = clean_tokens(label, stop_words)

            # Limpeza do valor (apenas números)
            cleaned_value = clean_value(value)

            # Adiciona valores não nulos e não vazios ao array
            if value is not None:
                non_empty_values.append((label_tokens, cleaned_value, confidence))

            # Verifica e valida CNPJ
            if len(cleaned_value) == 14 and cleaned_value.isdigit():
                validated_cnpj = validate_cnpj(cleaned_value)
                if validated_cnpj:
                    update_confidence(confidence_dict, "CNPJ_emissor", validated_cnpj, confidence)

            # Verifica e valida CPF
            elif len(cleaned_value) == 11 and cleaned_value.isdigit():
                validated_cpf = validate_cpf(cleaned_value)
                if validated_cpf:
                    update_confidence(confidence_dict, "CNPJ_CPF_consumidor", validated_cpf, confidence)

            # Outras verificações
            elif "VENDOR_NAME" in field_type or "NAME" in field_type:
                update_confidence(confidence_dict, "nome_emissor", value, confidence)

            elif "ADDRESS_BLOCK" in field_type:
                cep_match = re.search(r"\d{5}-\d{3}", value)
                update_confidence(confidence_dict, "endereco_emissor", value, confidence)
                if cep_match:
                    confidence_dict["endereco_emissor"]["value"] += f" {cep_match.group()}"

            elif "DATE" in field_type or re.match(r"\d{2}/\d{2}/\d{4}", value):
                update_confidence(confidence_dict, "data_emissao", value, confidence)

            elif ("AMOUNT_PAID" in field_type or "TOTAL" in field_type):
                update_confidence(confidence_dict, "valor_total", value, confidence)

            elif "INVOICE_RECEIPT_ID" in field_type or any(token in label_tokens for token in ["extrato"]):
                update_confidence(confidence_dict, "numero_nota_fiscal", value, confidence)

            elif any(token in label_tokens for token in ["serie", "série", "sat"]):
                update_confidence(confidence_dict, "serie_nota_fiscal", value, confidence)

        # Verifica a forma de pagamento e outros valores a partir do array de valores não vazios
        for label_tokens, cleaned_value, confidence in non_empty_values:
            if any(match_percentage(token, "dinheiro") > similarity_threshold for token in label_tokens):
                update_confidence(confidence_dict, "forma_pgto", "dinheiropix", confidence)
                update_confidence(confidence_dict, "valor_total", cleaned_value, confidence)

    # Caso o CNPJ_emissor ou C NPJ_CPF_consumidor sejam None, buscar nos Blocks
        if not confidence_dict.get("CNPJ_emissor") or not confidence_dict.get("CNPJ_CPF_consumidor"):
            for field in document.get("Blocks", []):
                value = field.get("Text", "").strip()
                cleaned_value = clean_value(value)

                if (len(cleaned_value) == 14 and cleaned_value.isdigit()):
                    validated_cnpj = validate_cnpj(cleaned_value)
                    if validated_cnpj:
                        update_confidence(confidence_dict, "CNPJ_emissor", validated_cnpj, confidence)
                if (len(cleaned_value) == 11 and cleaned_value.isdigit()):
                    validated_cpf = validate_cpf(cleaned_value)            
                    if validated_cpf:
                        update_confidence(confidence_dict, "CNPJ_CPF_consumidor", validated_cpf, confidence)

    # Adiciona os valores com maior confiança ao dicionário final
    for key, item in confidence_dict.items():
        extracted_info[key] = item["value"]

    return extracted_info

def move_image(bucket_name, object_key, payment_method):
    """Move a imagem para a pasta correta no bucket S3 com base na forma de pagamento."""
    target_folder = "dinheiro" if payment_method == "dinheiropix" else "outros"
    target_key = f"{target_folder}/{object_key.split('/')[-1]}"

    try:
        # Copia o objeto para a nova localização
        s3.copy_object(Bucket=bucket_name, CopySource={"Bucket": bucket_name, "Key": object_key}, Key=target_key)

        # Remove o objeto original
        s3.delete_object(Bucket=bucket_name, Key=object_key)
    except Exception as e:
        raise RuntimeError(f"Erro ao mover a imagem no S3: {str(e)}")


def lambda_handler(event, context):
    # Acessa a chave Payload -> body
    payload = event.get('Payload', {})
    body = payload.get('body', None)

    if not body:
        return {
            'statusCode': 400,
            'body': json.dumps('Corpo não encontrado no evento.')
        }

    # Se o corpo for uma string JSON, converta-o para um dicionário
    try:
        body_data = json.loads(body)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps('Erro ao decodificar o corpo do evento.')
        }

    # Acesse o campo 'extracted_data' dentro de body_data
    extracted_data = body_data.get('extracted_data')
    bucket_name = body_data.get('bucket_name')
    object_key = body_data.get('object_key')

    if not extracted_data:
        return {
            'statusCode': 400,
            'body': json.dumps('Dados extraídos não encontrados no evento.')
        }
    
    extracted_info = extract_information(extracted_data)

    try:
        move_image(bucket_name, object_key, extracted_info.get("forma_pgto", "outros"))
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Erro ao mover a imagem: {str(e)}")
        }
    # Extrai as informações

    return extracted_info

