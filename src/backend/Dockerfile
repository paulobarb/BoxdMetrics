# Builder
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements-lock.txt .

RUN pip install --no-cache-dir -r requirements-lock.txt -t /build

# Lambda Image
FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /build ${LAMBDA_TASK_ROOT}

COPY src/ ${LAMBDA_TASK_ROOT}/src/

ENV PYTHONPATH="${LAMBDA_TASK_ROOT}/src"

CMD ["src.backend.main.handler"]
