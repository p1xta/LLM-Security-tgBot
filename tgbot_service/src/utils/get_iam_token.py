import httpx

async def get_iam_token_on_YC_vm(client: httpx.AsyncClient):
    header = {
        "Metadata-Flavor":"Google"
    }
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    response = await client.get(url=url, headers=header)
    json_response = response.json()
    return json_response['access_token']