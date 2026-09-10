INTEGRATION_OPENAPI = {
    "openapi": "3.1.0",
    "info": {
        "title": "PRINTFLOW Integration API",
        "version": "1.0.0",
        "description": (
            "API read-only para integração segura com assistentes e ferramentas externas. "
            "Não expõe senhas, JWT, chave de recovery ou token do Agent."
        ),
    },
    "servers": [
        {"url": "https://printflow-api-genesis.onrender.com/api/v1/integration"}
    ],
    "components": {
        "securitySchemes": {
            "IntegrationKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Printflow-Integration-Key",
            }
        },
        "schemas": {
            "AgentSnapshot": {
                "type": "object",
                "properties": {
                    "online": {"type": "boolean"},
                    "stale": {"type": "boolean"},
                    "communication_state": {"type": "string"},
                    "status": {"type": ["string", "null"]},
                    "name": {"type": ["string", "null"]},
                    "version": {"type": ["string", "null"]},
                    "last_seen": {"type": ["string", "null"], "format": "date-time"},
                    "last_error": {"type": ["string", "null"]},
                },
            },
            "CompanySnapshot": {
                "type": "object",
                "properties": {
                    "uuid": {"type": "string"},
                    "name": {"type": "string"},
                    "plan": {"type": "string"},
                    "active": {"type": "boolean"},
                    "agent": {"$ref": "#/components/schemas/AgentSnapshot"},
                    "printers": {
                        "type": "object",
                        "properties": {
                            "active": {"type": "integer"},
                            "online": {"type": "integer"},
                            "offline": {"type": "integer"},
                        },
                    },
                    "alerts_open": {"type": "integer"},
                    "onboarding": {"type": "object", "additionalProperties": True},
                    "commercial": {"type": "object", "additionalProperties": True},
                },
            },
            "Printer": {"type": "object", "additionalProperties": True},
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {"type": "string"},
                    "active": {"type": "boolean"},
                    "created_at": {"type": ["string", "null"], "format": "date-time"},
                },
            },
            "Alert": {"type": "object", "additionalProperties": True},
        },
    },
    "security": [{"IntegrationKey": []}],
    "paths": {
        "/status": {
            "get": {
                "operationId": "getIntegrationStatus",
                "summary": "Obtém o status geral do PRINTFLOW",
                "description": "Retorna empresas, Agents online, impressoras ativas e alertas abertos.",
                "responses": {"200": {"description": "Status geral"}},
            }
        },
        "/companies": {
            "get": {
                "operationId": "listCompanies",
                "summary": "Lista empresas monitoradas",
                "responses": {
                    "200": {
                        "description": "Empresas",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/CompanySnapshot"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/companies/{company_uuid}": {
            "get": {
                "operationId": "getCompany",
                "summary": "Obtém o estado de uma empresa",
                "parameters": [
                    {
                        "name": "company_uuid",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Empresa",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CompanySnapshot"}
                            }
                        },
                    }
                },
            }
        },
        "/companies/{company_uuid}/printers": {
            "get": {
                "operationId": "listCompanyPrinters",
                "summary": "Lista impressoras de uma empresa",
                "parameters": [
                    {
                        "name": "company_uuid",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Impressoras",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Printer"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/companies/{company_uuid}/users": {
            "get": {
                "operationId": "listCompanyUsers",
                "summary": "Lista usuários de uma empresa",
                "parameters": [
                    {
                        "name": "company_uuid",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Usuários",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/User"},
                                }
                            }
                        },
                    }
                },
            }
        },
        "/companies/{company_uuid}/alerts": {
            "get": {
                "operationId": "listCompanyAlerts",
                "summary": "Lista alertas operacionais de uma empresa",
                "parameters": [
                    {
                        "name": "company_uuid",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Alertas",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Alert"},
                                }
                            }
                        },
                    }
                },
            }
        },
    },
}
