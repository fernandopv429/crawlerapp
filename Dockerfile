# Usa uma imagem oficial e leve do Python
FROM python:3.11-slim

# Impede que o Python grave arquivos .pyc no disco e força o log direto no terminal
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia apenas o arquivo de dependências primeiro (otimiza o cache do Docker)
COPY requirements.txt .

# Instala as bibliotecas do Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala o navegador Chromium e todas as dependências de sistema (OS) necessárias
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Agora copia o resto do seu código (o main.py) para dentro do container
COPY . .

# Expõe a porta que o FastAPI vai usar
EXPOSE 8000

# Comando para iniciar o servidor Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
