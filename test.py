import asyncio
import datetime
import json
from typing import Literal
import uuid
from Classes.CE_User import CEUser
from Modules import Mongo_Reader, CEAPIReader, SupabaseReader

print(SupabaseReader.get_user('d7cb0869-5ed9-465c-87bf-0fb95aaebbd5'))