FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV OPENAI_API_KEY=""
ENV SLACK_WEBHOOK_URL=""

ENTRYPOINT ["python", "run_eval.py"]
CMD ["--prompt", "prompts/classifier_v2.yaml"]
