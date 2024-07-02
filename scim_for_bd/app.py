from flask import Flask, request
import logging
import os
import json
import requests
import re
from blackduck.HubRestApi import HubInstance

api = Flask(__name__)

MAX_LIMIT=100
BD_URL=os.getenv("BD_URL")

def getToken(request):
    global BD_URL
    if request and request.headers.get("Authorization"):
        # matching_headers = [string for string in dict(request.headers) if "bdurl" == string.casefold()]
        # if matching_headers and len(matching_headers) == 1:
        #     BD_URL = request.headers.get(matching_headers[0])
        # else:
        #     response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"BD_Url\" was missing!"))
        #     response.mimetype = "application/scim+json"
        #     response.status_code = "401"
        #     return response
        return request.headers.get("Authorization").split('Bearer')[-1].strip()

# API Endpoint to get used Schemas
@api.route('/scim/v2/Schemas', methods=['GET'])
def getSchema():
    for root, dirs, files in os.walk(os.getcwd()):
        for filename in files:
            if filename == "scimUserSchema.json":
                with open(root + os.path.sep + filename, "r") as schemaFile:
                    response = api.make_response(json.dumps(json.load(schemaFile), indent=3))
                    response.mimetype = "application/scim+json"
                    response.status_code = "200"
                    response = addHeadersForSwagger(response)
                    logging.info(response.json)
                    return response

# API Enpoint to add user. If user exists already then HTTP Error 409 returned.
@api.route('/scim/v2/Users', methods=['POST'])
def addUser():
    global BD_URL
    try:
        if request.json:
            access_token = getToken(request)
            if access_token:
                hub = HubInstance(BD_URL, api_token=access_token, write_config_flag=False)
                scimUser = createBDUser(request.json)
                #Test if user already exists
                parameters = {"limit":100,"q": f"userName:{scimUser['userName']}"}
                users = hub.get_users(parameters)
                if users and users["totalCount"] > 0:
                    response = api.make_response(createSCIMErrorResponse("uniqueness", f"Given userName {scimUser['userName']} already exists.", "409"))
                    response.mimetype = "application/scim+json"
                    response.status_code = "409"
                    response = addHeadersForSwagger(response)
                    return response
                userURL = hub.create_user(scimUser)
                user = hub.get_user_by_url(userURL)
                if user:
                    response = api.make_response(createUserSCIMResponse(user))
                    response.mimetype = "application/scim+json"
                    response.status_code = "201"
                    response = addHeadersForSwagger(response)
                    return response
            else:
                response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"token\" was missing!"))
                response.mimetype = "application/scim+json"
                response.status_code = "401"
                response = addHeadersForSwagger(response)
                return response
        else:
            response = api.make_response(createSCIMErrorResponse(scimType="invalidValue", status_code="400", detail="User data was missing!"))
            response.mimetype = "application/scim+json"
            response.status_code = "400"
            response = addHeadersForSwagger(response)
            return response
    except Exception as ex:
        response = api.make_response(createSCIMErrorResponse(scimType="invalidValue", status_code="400", detail=f"Request is unparsable, syntactically incorrect, or violates schema, error: {str(ex)}"))
        response.mimetype = "application/scim+json"
        response.status_code = "400"
        response = addHeadersForSwagger(response)
        return response

# API Enpoint to update user from Black Duck. If user not exists, then http error 404 returned,
# if user update success, then updated user is returned.
# Id can be Black Duck User Id or userName
@api.route('/scim/v2/Users/<string:Id>', methods=['PATCH'])
def updateUser(Id):
    global BD_URL
    access_token = getToken(request)
    if access_token:
        hub = HubInstance(BD_URL, api_token=access_token, write_config_flag=False)
        users = get_user_by_id(hub, Id)
        if not users or not "totalCount" in users or users["totalCount"] == 0: 
            #If user is not found with ID then trying to find user by using Id as an username.
            parameters = {"limit":100,"q": f"userName:{Id}"}
            users = hub.get_users(parameters)
        if users and users["totalCount"] > 0:
            if request.json:
                for operation in request.json["Operations"]:
                    if operation["op"].casefold() == "replace":
                        if "path" in operation and operation["path"] == "emails[type eq \"work\"].value":
                            users["items"][0]["email"] = operation["value"]
                        elif "path" in operation and operation["path"] == "userName":
                            users["items"][0]["userName"] = operation["value"]
                        elif "path" in operation and operation["path"] == "active":
                            users["items"][0]["active"] = operation["value"]
                        elif "path" in operation and operation["path"] == "name.givenName":
                            users["items"][0]["firstName"] = operation["value"]
                        elif "path" in operation and operation["path"] == "name.familyName":
                            users["items"][0]["lastName"] = operation["value"]
                        else:
                            if "name.familyName" in operation["value"]:
                                users["items"][0]["lastName"] = operation["value"]["name.familyName"]
                            if "emails[type eq \"work\"].value" in operation["value"]:
                                users["items"][0]["email"] = operation["value"]["emails[type eq \"work\"].value"]
                            if "userName" in operation["value"]:
                                users["items"][0]["userName"] = operation["value"]["userName"]
                            if "name.givenName" in operation["value"]:
                                users["items"][0]["firstName"] = operation["value"]["name.givenName"]
                            if "active" in operation["value"]:
                                users["items"][0]["active"] = operation["value"]["active"]
                hub.update_user_by_url(users["items"][0]["_meta"]["href"], users["items"][0])
                response = api.make_response(createUserSCIMResponse(users["items"][0]))
                response.mimetype = "application/scim+json"
                response.status_code = "200"
                response = addHeadersForSwagger(response)
                return response
        else:
            response = api.make_response(createSCIMErrorResponse(scimType="invalidValue", status_code="404", detail=f"Username: {Id} not found!"))
            response.mimetype = "application/scim+json"
            response.status_code = "404"
            response = addHeadersForSwagger(response)
            return response
    else:
        response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"token\" was missing!"))
        response.mimetype = "application/scim+json"
        response.status_code = "401"
        response = addHeadersForSwagger(response)
        return response

# API Endpoint to delete user, but Black Duck is not supporting this, so user is only inactivated.
@api.route('/scim/v2/Users/<string:Id>', methods=['DELETE'])
def deleteUser(Id):
    global BD_URL
    access_token = getToken(request)
    if access_token:
        hub = HubInstance(BD_URL, api_token=access_token, write_config_flag=False)
        users = get_user_by_id(hub, Id)
        if not users or not "totalCount" in users or users["totalCount"] == 0: 
            #If user is not found with ID then trying to find user by using Id as an username.
            parameters = {"limit":100,"q": f"userName:{Id}"}
            users = hub.get_users(parameters)
        if users and users["totalCount"] > 0:
            if request.json:
                for operation in request.json["Operations"]:
                    if operation["op"].casefold() == "replace":
                        if "path" in operation and operation["path"] == "active":
                            users["items"][0]["active"] = operation["value"]
            else:
                users["items"][0]["active"] = False
            hub.update_user_by_url(users["items"][0]["_meta"]["href"], users["items"][0])
            response = api.make_response("")
            response.status_code = "204"
            response = addHeadersForSwagger(response)
            return response
        else:
            response = api.make_response(createSCIMErrorResponse(scimType="invalidValue", status_code="404", detail=f"Username: {Id} not found!"))
            response.mimetype = "application/scim+json"
            response.status_code = "404"
            response = addHeadersForSwagger(response)
            return response
    else:
        response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"token\" was missing!"))
        response.mimetype = "application/scim+json"
        response.status_code = "401"
        response = addHeadersForSwagger(response)
        return response

# API Endpoint to get user info for given Id or username. If not found, then http error 404 returned otherwise
# returned the existing user info.
# Id can be Black Duck User Id or userName
@api.route('/scim/v2/Users/<string:Id>', methods=['GET'])
def getUser(Id):
    global BD_URL
    access_token = getToken(request)
    if access_token:
        hub = HubInstance(BD_URL, api_token=access_token, write_config_flag=False)
        users = get_user_by_id(hub, Id)
        logging.info(users)
        if not users or not "totalCount" in users or users["totalCount"] == 0: 
            #If user is not found with ID then trying to find user by using Id as an username.
            parameters = {"limit":100,"q": f"userName:{Id}"}
            users = hub.get_users(parameters)
        if users and users["totalCount"] > 0:
            response = api.make_response(createUserSCIMResponse(users["items"][0]))
            response.mimetype = "application/scim+json"
            response.status_code = "200"
            response = addHeadersForSwagger(response)
            return response
        else:
            response = api.make_response(createSCIMErrorResponse(scimType="invalidValue", status_code="404", detail=f"User: {Id} not found!"))
            response.mimetype = "application/scim+json"
            response.status_code = "404"
            response = addHeadersForSwagger(response)
            return response
    else:
        response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"token\" was missing!"))
        response.mimetype = "application/scim+json"
        response.status_code = "401"
        response = addHeadersForSwagger(response)
        return response

# API Endpoint to get users from Black Duck. This API Endpoint supports filttering.
# Only following filtters are supported: userName and email, and supported operation is only eq = equals.
@api.route('/scim/v2/Users', methods=['GET'])
def getUsers():
    global BD_URL
    access_token = getToken(request)
    if access_token:
        hub = HubInstance(BD_URL, api_token=access_token, write_config_flag=False)
        parameters = {"limit":MAX_LIMIT}
        #check are there any other filters given
        if request.query_string:
            #Only userName and email are currently supported
            query_string = requests.utils.unquote(request.query_string)
            if query_string.find('eq') > 0 and query_string.find('userName') > 0:
                parameters["q"] = "userName:" + re.split('\+eq\+|eq',query_string)[-1].strip().replace('\"','')
            elif query_string.find('eq') > 0 and query_string.find('email') > 0:
                parameters["q"] = "email:" + re.split('\+eq\+|eq',query_string)[-1].strip().replace('\"','')
        users = hub.get_users(parameters=parameters)
        logging.info(users)
        if users:
            all_data = users
            if "totalCount" in users:
                total = users['totalCount']
                downloaded = MAX_LIMIT
                while total > downloaded:
                    parameters["offset"] = downloaded
                    users = hub.get_users(parameters=parameters)
                    all_data['items'] = all_data['items'] + users['items']
                    downloaded += MAX_LIMIT
            scimUsersResponse = {"schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"], "totalResults": users["totalCount"], "itemsPerPage": MAX_LIMIT, "startIndex": 1}
            scimUserReources = []
            for user in all_data["items"]:
                scimUserReources.append(createUserSCIMResponse(user))
            scimUsersResponse['Reouces'] = scimUserReources
        response = api.make_response(scimUsersResponse)
        response.mimetype = "application/scim+json"
        response.status_code = "200"
        response = addHeadersForSwagger(response)
        return response
    else:
        response = api.make_response(createSCIMErrorResponse(scimType="invalidSyntax", status_code="401", detail="Header: \"token\" was missing!"))
        response.mimetype = "application/scim+json"
        response.status_code = "401"
        response = addHeadersForSwagger(response)
        return response


def get_user_by_id(hub, user_id):
    url = BD_URL + "/api/users/{}".format(user_id)
    headers = {'Accept': 'application/vnd.blackducksoftware.user-4+json'}
    response = hub.execute_get(url, custom_headers=headers)
    jsondata = response.json()
    return jsondata

def createBDUser(scimUser):
    if scimUser:
        bdUser = {
            "userName" : scimUser["userName"],
            "firstName" :  scimUser["name"]["givenName"],
            "lastName" :  scimUser["name"]["familyName"],
            "email" :  scimUser["emails"][0]["value"],
            "active" : True,
            "type" : "EXTERNAL"
        }
        return bdUser

def createUserSCIMResponse(user):
    scimUser = {"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]}
    id = user["_meta"]["href"].split('/')[-1]
    if id:
        scimUser["id"] = id
    scimUser["userName"] = user["userName"]
    if "externalUserName" in user and user["externalUserName"]:
        scimUser["externalId"] = user["externalUserName"]
    scimUser["displayName"] = f'{user["firstName"]} {user["lastName"]}'
    scimUser["name"] = {
        "givenName": user["firstName"],
        "familyName": user["lastName"],
        "formatted": f'{user["firstName"]} {user["lastName"]}'}
    scimUser["emails"] = [{
        "type": "work",
        "value": user["email"],
        "primary": True }]
    scimUser["active"] = user["active"]
    scimUser["meta"] = {
        "resourceType": "User",
        "location": user["_meta"]["href"]}
    return scimUser

def createSCIMErrorResponse(scimType,detail, status_code):
    error = {
     "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
     "scimType": scimType,
     "detail": detail,
     "status": status_code
    }
    return json.dumps(error)

def addHeadersForSwagger(response):
    response.headers["X-Requested-With"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-requested-with"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST,GET,DELETE,OPTIONS"
    return response

if __name__ == '__main__':
    try:
        api.run(debug=False)
    except Exception as ex:
        logging.error("Error: " + str(ex))
        exit()

