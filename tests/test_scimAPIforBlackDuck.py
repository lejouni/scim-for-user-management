import pytest
import requests
import logging
import json
import string
import random

username="Test_lehto_65VYM"
user_endpoint = "/scim/v2/Users"

def getHeaders(bd_token):
   return {
        "Authorization": "Bearer " + bd_token,
        "content-Type": "application/scim+json"
    }

@pytest.mark.run(order=1)
def test_getSchemas(scim_url, bd_token):
    schema_endpoint = "/scim/v2/Schemas"
    response = requests.get(scim_url + schema_endpoint, headers=getHeaders(bd_token))
    logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
    assert response.status_code == 200

# @pytest.mark.run(order=2)
# def test_addUser(scim_url, bd_token):
#     global username, user_endpoint
#     logging.info(create_addScimUser())
#     response = requests.post(scim_url + user_endpoint, json=create_addScimUser(), headers=getHeaders(bd_token))
#     logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
#     logging.info(json.dumps(response.json(), indent=3))
#     assert response.status_code == 201

@pytest.mark.run(order=6)
def test_getUsers(scim_url, bd_token):
    global username, user_endpoint
    response = requests.get(scim_url + user_endpoint, headers=getHeaders(bd_token))
    logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
    logging.info(json.dumps(response.json(), indent=3))
    assert response.status_code == 200

@pytest.mark.run(order=4)
def test_getUser(scim_url, bd_token):
    global username, user_endpoint
    response = requests.get(scim_url + user_endpoint + "/" + username, headers=getHeaders(bd_token))
    logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
    logging.info(json.dumps(response.json(), indent=3))
    assert response.status_code == 200

@pytest.mark.run(order=3)
def test_updateUser(scim_url, bd_token):
    global username, user_endpoint
    response = requests.patch(scim_url + user_endpoint + "/" + username, json=create_updateScimUser() ,headers=getHeaders(bd_token))
    logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
    logging.info(json.dumps(response.json(), indent=3))
    assert response.status_code == 200

@pytest.mark.run(order=5)
def test_deleteUser(scim_url, bd_token):
    global username, user_endpoint
    response = requests.delete(scim_url + user_endpoint + "/" + username, json=create_deleteScimUser(), headers=getHeaders(bd_token))
    logging.info(f"HTTP_STATUS_CODE: {response.status_code}")
    assert response.status_code == 204

def create_addScimUser():
    global username
    username = f"Test_lehto_{''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}"
    scimUser = {
        "schemas": [
            "urn:ietf:params:scim:schemas:core:2.0:User",
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"],
        "externalId": "0a21f0f2-8d2a-4f8e-bf98-7363c4aed4ef",
        "userName": username,
        "active": True,
        "emails": [{
            "primary": True,
            "type": "work",
            "value": "lehto@synopsys.com"
        }],
        "meta": {
            "resourceType": "User"
        },
        "name": {
            "formatted": "Jouni Lehto",
            "familyName": "Lehto",
            "givenName": "Jouni"
        },
        "roles": []
    }
    return scimUser

def create_updateScimUser():
    scimUser = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
            "op": "replace",
            "path": "emails[type eq \"work\"].value",
            "value": "lehto.updated@synopsys.com"
            },
            {
            "op": "replace",
            "path": "name.familyName",
            "value": "Lehto_updated"
            }
        ]
    }
    return scimUser

def create_deleteScimUser():
    scimUser = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {
            "op": "replace",
            "path": "active",
            "value": False
            }
        ]
    }
    return scimUser