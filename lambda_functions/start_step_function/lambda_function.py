import json
import boto3
import time
import os

# Inicializa os clientes AWS
client = boto3.client('stepfunctions')
s3_client = boto3.client('s3')

# ARN da máquina de estados
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')

# Nome do bucket S3
BUCKET_NAME = os.environ.get('DEST_BUCKET')

# Verificação do variáveis de ambiente
if not STATE_MACHINE_ARN:
    raise ValueError("A variável de ambiente DEST_BUCKET não está configurada.")

if not BUCKET_NAME:
    raise ValueError("A variável de ambiente DEST_BUCKET não está configurada.")

def start_step_function(event):
    """
    Função para iniciar a execução da Step Function.
    Armazena os dados no S3 e retorna o ARN da execução.

    Args:
        event (dict): Evento recebido pela Lambda.

    Returns:
        str: ARN da execução da Step Function.
    """
    try:
        # Formata os dados de entrada como JSON
        input_data = json.dumps(event)

        # Nome do arquivo no S3
        file_name = 'input_data.json'

        # Faz o upload do JSON para o S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=input_data)

        # Prepara a entrada para a Step Function
        input_for_state_machine = {
            "bucket_name": BUCKET_NAME,
            "file_name": file_name
        }

        # Dispara a execução da Step Function
        response = client.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(input_for_state_machine)
        )

        # Retorna o ARN da execução
        return response.get('executionArn', '')

    except Exception as e:
        raise RuntimeError(f"Erro ao iniciar a Step Function: {str(e)}")


def get_step_function_response(execution_arn):
    """
    Função para monitorar o status da Step Function e retornar a saída.

    Args:
        execution_arn (str): ARN da execução da Step Function.

    Returns:
        dict: Dados de saída da Step Function.
    """
    try:
        # Espera pela conclusão da Step Function
        while True:
            execution_response = client.describe_execution(
                executionArn=execution_arn
            )
            
            status = execution_response['status']

            if status == 'SUCCEEDED':
                # Processa e retorna a saída
                output = execution_response.get('output', '{}')
                return json.loads(output)
            elif status in ['FAILED', 'TIMED_OUT', 'CANCELLED']:
                raise RuntimeError("Step Function falhou, expirou ou foi cancelada.")

    except Exception as e:
        raise RuntimeError(f"Erro ao monitorar a Step Function: {str(e)}")


def lambda_handler(event, context):
    """
    Função principal da Lambda para orquestrar o processo.

    Args:
        event (dict): Evento recebido pela Lambda.
        context: Contexto de execução da Lambda.

    Returns:
        dict: Resposta formatada para o cliente.
    """
    try:
        # Inicia a Step Function
        execution_arn = start_step_function(event)

        # Obtém a resposta da Step Function
        response_data = get_step_function_response(execution_arn)

        # Retorna a resposta para o cliente
        return response_data

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "Error",
                "message": str(e)
            }, indent=4, ensure_ascii=False)
        }
