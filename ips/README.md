```bash
docker build -t ip_backend .
```

```bash
docker run -v $(pwd)/db.json:/db.json -d --name ip_backend -p 8000:8000 ip_backend
```

Documentation on http://127.0.0.1:8000/docs or http://127.0.0.1:8000/redoc
