# Git Project Embryo

## Overview
Key abilities:
- instantiate a git repository
- optionally setup a remote
- provide a base `.gitignore`, that covers a good amount of temporary files 

## Usage
The most simple usage will initialize a repository in the current directory
```
embryo create git-project
```

Additionally it can setup an initialized repository with a specified remote name and path.
```
embryo create git-project \
  --remote.name lamer-origin \
  --remote.path git@lib.land:lamer-name/my-lame-project.git
```
The argument `--remote.name` is not required, and when omitted, then the default name will become `origin`.