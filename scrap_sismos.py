import requests
import boto3
import uuid
from datetime import datetime

def lambda_handler(event, context):
    anio = datetime.utcnow().year
    url = f"https://ultimosismo.igp.gob.pe/api/ultimo-sismo/ajaxb/{anio}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"
    }

    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': f'Error al acceder al API del IGP ({response.status_code})'
        }

    data = response.json()

    if isinstance(data, dict):
        for key in ['data', 'sismos', 'items', 'results']:
            if key in data and isinstance(data[key], list):
                data = data[key]
                break

    if not isinstance(data, list) or len(data) == 0:
        return {
            'statusCode': 404,
            'body': 'La respuesta del IGP no contiene lista de sismos'
        }

    sismos = data[:10]

    dynamodb = boto3.resource('dynamodb')
    tabla = dynamodb.Table('TablaSismosIGP')

    scan = tabla.scan()
    with tabla.batch_writer() as batch:
        for item in scan['Items']:
            batch.delete_item(Key={'id': item['id']})

    guardados = []
    for i, sismo in enumerate(sismos, start=1):
        item = {k: str(v) if v is not None else '' for k, v in sismo.items()}
        item['#'] = i
        item['id'] = str(uuid.uuid4())
        tabla.put_item(Item=item)
        guardados.append(item)

    return {
        'statusCode': 200,
        'body': {
            'cantidad': len(guardados),
            'sismos': guardados
        }
    }
