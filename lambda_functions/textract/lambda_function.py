import boto3
import json

# def print_labels_and_values(field):
#     """Imprime os rótulos e valores detectados."""
#     if "LabelDetection" in field:
#         print("Label Detection - Confidence: {:.2f}, Text: {}".format(
#             field["LabelDetection"]["Confidence"],
#             field["LabelDetection"]["Text"]
#         ))
#     else:
#         print("Label Detection - No labels returned.")

#     if "ValueDetection" in field:
#         print("Value Detection - Confidence: {:.2f}, Text: {}".format(
#             field["ValueDetection"]["Confidence"],
#             field["ValueDetection"]["Text"]
#         ))
#     else:
#         print("Value Detection - No values returned.")

def process_text_detection(bucket, document):
    """Processa a detecção de texto em um documento armazenado no S3."""
    # Inicializa o cliente Textract
    client = boto3.client('textract', region_name="us-east-1")

    # Chama o Textract para analisar o documento
    response = client.analyze_expense(
        Document={'S3Object': {'Bucket': bucket, 'Name': document}}
    )

    # # Processa os documentos de despesas retornados
    # for expense_doc in response["ExpenseDocuments"]:
    #     # Imprime os campos de despesas
    #     for line_item_group in expense_doc["LineItemGroups"]:
    #         for line_item in line_item_group["LineItems"]:
    #             for expense_field in line_item["LineItemExpenseFields"]:
    #                 print_labels_and_values(expense_field)
    #                 print()

    #     print("Summary:")
    #     for summary_field in expense_doc["SummaryFields"]:
    #         print_labels_and_values(summary_field)
    #         print()

    # Retorna a resposta do Textract
    return response

def lambda_handler(event, context):
    # Acessa a chave Payload -> body
    payload = event.get("Payload", {})
    body = payload.get("body", None)

    # Verifica se body existe e converte de JSON string para dicionário, se necessário
    if body:
        if isinstance(body, str):
            body = json.loads(body)  # Decodifica JSON string para dicionário

        bucket_name = body.get('bucket_name')
        object_key = body.get('object_key')

        if not bucket_name or not object_key:
            raise ValueError("As chaves 'bucket_name' e 'object_key' são obrigatórias no corpo do evento.")

        extracted_data = process_text_detection(bucket_name, object_key)
  
    else:
        raise ValueError("O evento não contém a chave 'body'.")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'Processamento completo!',
            'extracted_data': extracted_data,
            'bucket_name': bucket_name,
            'object_key': object_key
        })
    }
