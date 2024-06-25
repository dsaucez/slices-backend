# Use official and latest/particular Golang image
FROM golang:1.22

# Set working directory
WORKDIR /app

# Copy the source code of this folder inside the container
COPY . .

# Download and install dependencies
RUN go get -d -v .

# Build the Go app
RUN go build -o core .

#Expose the port
EXPOSE 8008

#Run the executable
CMD ["./core/openapi"]
