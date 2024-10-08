```bash
docker build -t ip_backend .
```

Update the `credentials.json` to use your SLICES S3 access and secret key to
access the storage.

```bash
docker run --rm -v $(pwd)/db.json:/db.json -v $(pwd)/credentials.json:/credentials.json -d --name ip_backend -p 8000:8000 ip_backend
```

Documentation on http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc
