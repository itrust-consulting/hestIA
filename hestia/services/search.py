from typing import Dict, Any, List

from hestia.protocols.db import DBProvider
from hestia.schemas.api import Query

class Retriever:

    def __init__(self, 
                 provider: DBProvider):
        self.provider = provider
    
    def retrieve(self,
                 collection: str,
                 query: Query, 
                 options: Dict[str, Any]
                 ) -> List:

        return self.provider.search(collection,
                                    query,
                                    options=options)
