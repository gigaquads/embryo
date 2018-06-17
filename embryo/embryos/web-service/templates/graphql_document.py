from pybiz import BizObject, Relationship

from ..api import api
from .user import User


class GraphQLDocument(BizObject):
    """
    This class defines the top-level structure permitted by a GraphQL query
    through the use of `Relationship` declarations, for example:

    ```python3
    query = '''
        {
            user {
                name
                email
            }
        }
    ```

    This example assumes that a `user` relationship exists.
    """

    user = Relationship(User)

    @api.get('/graphql')
    def query(q: str=None):
        """
        Execute a GraphQL query string.
        """
        return GraphQLDocument.graphql_engine.query(q)

