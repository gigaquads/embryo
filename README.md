# Embryo

## What is an embryo?
Embryo began as a small internal tool for scaffolding new projects. After my friend and I began using it more seriously, it started to take shape. In the context of the Embryo program, _an_ embryo refers to a plain ol' directory that contains at least one essential file, `tree.yml`, which specifies the templated names and locations of the files and directories you want to create or verify in the filesystem. In addition to a tree file, embryos can contain static context, templates for rendering files, and hooks for custom logic and transformations along the way.

### Self-awareness
When an embryo is _hatched_ and files are created, metadata pertaining to which embryo was run, where changes were made, and what data was used to render its files is written to the filesystem in a "dot" file. Each embryo can resolve metadata stored in its ancestor and children directories at run time and have access to custom Python methods which they define.

This lets you write embryos that augment and work with each other. For example, you could create an embryo that initializes a new project and another that generates a source and test file for a new component of said project. When the "new component" embryo runs, it knows how to resolve the name of the project it's in and can therefore generate the correct import statements when rendering its templates.

### Virtual filesystem
A basic embryo will contain two main components: a `tree.yml` file and a `templates` directory. Unlike existing project scaffolding tools, the template files need not be arranged in the filesystem in a way that mirrors the structure defined in the tree file. Instead, you can store all your templates directly in the `templates` directory while tinkering with their arrangement in the tree file.

For example, consider the following embryo, called "project":

*`tree.yml`*
```ymal
---
- {{ project }}:
  - README.md
  - Makefile
  - {{ project|snake }}:
    - app.py
    - entities:
      - account.py: entity(account)
      - user.py: entity(user)
  - test:
    - test_account.py: unit_test(account)
    - test_user.py: unit_test(user)
...
```
