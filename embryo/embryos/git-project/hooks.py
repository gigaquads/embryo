import git


def pre_create(context):
    """
    Using the provided destination, initialize the git repository
    """
    dest = context['dest']
    g = git.cmd.Git(dest)
    g.init()
    return True
