import os
import base64
import boto3
import re
import time
import json
s3 = boto3.client('s3')

# Tipos de conteúdo permitidos
ALLOWED_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/bmp']

def lambda_handler(event, context):
    """Recebe uma imagem (via Base64 ou S3 URL), processa e envia ao S3."""
    try:
        # Extrair dados do evento
        bucket_name = event.get("bucket_name")
        object_key = event.get("file_name")

        # Processar arquivo S3
        file_data = fetch_file_from_s3(bucket_name, object_key)
        body = parse_json(file_data)

        # Decodificar imagem
        image_data, content_type, file_name = decode_image_data(body)

        # Validação de tipo de conteúdo
        validate_content_type(content_type)
        delete_file_from_s3(bucket_name, object_key)
        # Gerar nome único para o arquivo
        new_image_name = generate_unique_name(file_name)
        object_key = f"{new_image_name}.{content_type.split('/')[-1]}"

        # Enviar imagem para S3
        upload_to_s3(bucket_name, image_data, object_key)

        return {
            'statusCode': 200,
            'body': json.dumps({
                "bucket_name": bucket_name,
                "object_key": object_key,
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"Erro ao processar a imagem: {str(e)}"
            })
        }

def fetch_file_from_s3(bucket_name, object_key):
    """Recupera o arquivo do S3 e retorna seu conteúdo."""
    try:
        file_data = s3.get_object(Bucket=bucket_name, Key=object_key)
        return file_data['Body'].read().decode('utf-8')
    except Exception as e:
        raise ValueError(f"Erro ao buscar arquivo do S3: {str(e)}")

def parse_json(file_data):
    """Processa o conteúdo JSON do arquivo."""
    try:
        return json.loads(file_data).get("body")
    except Exception as e:
        raise ValueError(f"Erro ao processar JSON: {str(e)}")

def decode_image_data(body):
    """Decodifica os dados de imagem Base64 e retorna nome, tipo e dados da imagem."""
    input_text = base64.b64decode(body)
    image_data = re.search(rb'filename="([^"]+)"\r\nContent-Type: (.+?)\r\n\r\n(.*)', input_text, re.DOTALL)
    if not image_data:
        raise ValueError("Não foi possível extrair os dados da imagem.")
    
    file_name = image_data.group(1).decode('utf-8')
    content_type = image_data.group(2).decode('utf-8')
    image_bytes = image_data.group(3)
    return image_bytes, content_type, file_name

def validate_content_type(content_type):
    """Valida se o tipo de conteúdo é permitido."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Tipo de conteúdo não permitido: {content_type}. Apenas imagens são aceitas.")

def generate_unique_name(original_name):
    """Gera um nome único para a imagem usando o nome original e timestamp."""
    base_name = os.path.splitext(original_name)[0]
    timestamp = int(time.time())
    return f"{base_name}_{timestamp}"

def upload_to_s3(bucket_name, image_data, s3_key):
    """Faz o upload da imagem para o S3."""
    try:
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=image_data)
    except Exception as e:
        raise ValueError(f"Erro ao enviar a imagem para o S3: {str(e)}")

def delete_file_from_s3(bucket_name, object_key):
    """Exclui o arquivo JSON do S3 após o processamento."""
    try:
        s3.delete_object(Bucket=bucket_name, Key=object_key)
    except Exception as e:
        raise ValueError(f"Erro ao excluir o arquivo do S3: {str(e)}")
