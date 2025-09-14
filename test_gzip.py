#!/usr/bin/env python3
import requests

url = 'http://localhost:8000/job/rest/jobs/7389bef8-6544-4f7a-8c49-e6e3e5feedf7/cost-sets/estimate/'
headers = {'Accept': 'application/json', 'Accept-Encoding': 'gzip'}

print('Testing gzip compression on localhost...')
response = requests.get(url, headers=headers)

print(f'Status: {response.status_code}')
print(f'Content-Encoding: {response.headers.get("Content-Encoding", "none")}')
print(f'Content-Length: {response.headers.get("Content-Length", "unknown")}')
print(f'Actual response size: {len(response.content):,} bytes')
print(f'Compressed: {"gzip" in response.headers.get("Content-Encoding", "")}')
