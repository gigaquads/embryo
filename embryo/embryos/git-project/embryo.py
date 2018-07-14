import git

from appyratus.validation import fields
from embryo import Embryo, shout


class GitProjectEmbryo(Embryo):
    """
    # An embryo for initializing a git project
    """

    class context_schema(Embryo.Schema):
        """
        # Embryo Schema

        ## Fields
        - `remote`: Remote destination
            - `name`: name of the remote repository
            - `path`: path to the git repository


        """
        remote = fields.Object(
            dict(name=fields.Str(default='origin'), path=fields.Str())
        )

    def on_create(self, context):
        """
        Using the provided destination, initialize the git repository
        """
        # initialize git repository, this is non-destructive in the event that the repository
        # has already been initialized
        g = git.cmd.Git(self.destination)
        g.init()
        # instantiate the git repo
        repo = git.repo.base.Repo(self.destination)
        # remote management
        if 'remote' in self.context:
            remote_name = self.context['remote'].get('name', 'origin')
            remote_path = self.context['remote'].get('path')
            # check if remote exists, if it does then add it, otherwise let the user know
            remote_exists = git.remote.Remote(repo, remote_name).exists()
            if not remote_exists:
                git.remote.Remote.add(repo, remote_name, remote_path)
            else:
                shout("remote '{}' already exists".format(remote_name))
