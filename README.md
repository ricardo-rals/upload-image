# AWS Permissions Policy Setup

Este repositório contém uma política de permissões para a função Lambda que interage com o Amazon S3 e AWS Step Functions. Antes de usar, certifique-se de fazer as seguintes alterações e configurações:

## Alterações Necessárias

1. **Bucket S3**:
   - Substitua o `<BUCKET_NAME>` pelo nome do seu bucket S3 nas seguintes seções da política:
     - `"arn:aws:s3:::<BUCKET_NAME>/upload/*"`
     - `"arn:aws:s3:::<BUCKET_NAME>/input_data.json"`

2. **Região AWS**:
   - Substitua o `<REGION>` pela região onde sua conta AWS está configurada (exemplo: `us-east-1`).

3. **ID da Conta AWS**:
   - Substitua o `<ACCOUNT_ID>` pelo ID da sua conta AWS (exemplo: `442042529486`).

4. **Nome da Função Lambda**:
   - Substitua o `<LAMBDA_FUNCTION_NAME>` pelo nome da função Lambda usada para a ação desejada (exemplo: `api-upload-image`).

## Variáveis de Ambiente para Lambda

Na função Lambda `start_step_function`, você precisa configurar duas variáveis de ambiente:

1. **`BUCKET_NAME`**: Defina esta variável com o nome do seu bucket S3. Exemplo:
   - `BUCKET_NAME = ricardo-bucket-final`

2. **`STEP_FUNCTION_ARN`**: Defina esta variável com o ARN da sua Step Function. Exemplo:
   - `STEP_FUNCTION_ARN = arn:aws:states:us-east-1:442042529486:stateMachine:MyStateMachine`

Certifique-se de criar essas variáveis de ambiente na função Lambda antes de executar o fluxo de trabalho.

## Remover Comentários dos Arquivos JSON

**Importante**: Ao usar os arquivos JSON de política, remova **todos os comentários**. O formato JSON não permite comentários e, caso não os remova, poderá ocorrer erro ao tentar aplicar a política.
