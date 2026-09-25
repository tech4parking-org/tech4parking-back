# tech4parking-back

Backend do Tech4Parking: funções AWS Lambda (imagem Docker no ECR).

## Lambdas

| Lambda | Pasta | Função na AWS | Repositório ECR |
|--------|-------|---------------|-----------------|
| process_car_parking | `services/lambdas/process_car_parking` | `process_car_parking-lambda-processing` | `process_car_parking-ecr-lambda` |

A Lambda, o ECR, o IAM, a tabela DynamoDB `ParkingSpots`, a API Gateway e a regra IoT são criados pelo Terraform em [tech4parking-infra](https://github.com/tech4parking-org/tech4parking-infra).

### process_car_parking

Mantém a tabela `ParkingSpots` (chave `spot_id`) e atende dois tipos de evento:

**Sensor** ([tech4parking-iot](https://github.com/tech4parking-org/tech4parking-iot)), via regra IoT no tópico `parking_sensor`:

```json
{"spot_id": "A-01", "status": "ocupada", "distance": 12.34}
```

Atualiza `availability`, `distance` e `updated_at` da vaga.

**API** (`/spots` na API Gateway), usada pelo [tech4parking-front](https://github.com/tech4parking-org/tech4parking-front):

| Método | Rota | O que faz |
|--------|------|-----------|
| GET | `/spots` | lista as vagas |
| POST | `/spots` | cadastra uma vaga: `{"name", "latitude", "longitude", "availability"}` |
| DELETE | `/spots?spot_id=<id>` | remove uma vaga |

`availability` é `ocupada` ou `disponível`. As respostas trazem cabeçalhos CORS.

## Deploy

**Automático:** push na `main` alterando `services/lambdas/process_car_parking/**` (ou rodar o workflow manualmente). Secrets necessários no repositório: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`.

**Manual:**

```bash
AWS_ACCOUNT_ID=<id da conta> AWS_REGION=us-east-1 ./services/lambdas/process_car_parking/deploy.sh
```
