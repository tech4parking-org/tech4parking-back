FROM public.ecr.aws/lambda/python:3.12

# Copie os arquivos necessários
COPY process_car_parking.py requirements.txt ./

# Instale as dependências
RUN pip install -r requirements.txt

COPY process_car_parking.py ${LAMBDA_TASK_ROOT}

CMD ["process_car_parking.lambda_handler"]