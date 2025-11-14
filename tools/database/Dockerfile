FROM --platform=linux/arm64 public.ecr.aws/lambda/python:3.13

COPY piplock.txt ${LAMBDA_TASK_ROOT}
RUN pip install --upgrade pip
RUN pip install -r piplock.txt

COPY *.py ${LAMBDA_TASK_ROOT}

CMD ["lambda_function.lambda_handler"]
