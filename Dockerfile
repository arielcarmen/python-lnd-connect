# Use the Python 3 alpine official image
# https://hub.docker.com/_/python
FROM python:3-alpine

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY . .

# Install project dependencies
# RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x setup2.sh

RUN ./setup2.sh

# Run the web service on container startup.
CMD ["python", "main.py"]