FROM public.ecr.aws/docker/library/python:3.13-slim
WORKDIR /app

# Copy uv files
COPY piplock.txt ./

# Install dependencies
RUN pip3 install -r piplock.txt

# Copy agent code
COPY . .

# Expose port
EXPOSE 8080

# Run application
CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
