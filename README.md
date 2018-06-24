# Embryo

## Overview
Embryo began as a small internal tool for scaffolding new projects. After my friend and I began using it more seriously, it started to take shape. In the context of the Embryo program, _an_ embryo is a plain ol' directory that contains at least one essential file, `tree.yml`, which specifies the templated names and locations of the files and directories to create or verify in the filesystem. In addition to a tree file, embryos can contain static context, templates for rendering files, and hooks for custom logic and transformations along the way.

### Self-awareness
When an embryo is _hatched_ and files are created, metadata pertaining to which embryo was run, where changes were made, and what data was used to render its files is written to the filesystem in a "dot" file. Each embryo can resolve metadata stored in its ancestor and children directories at run time, and it has access to custom Python methods which those other embryos define.

This lets you write embryos that augment and work with each other. For example, you could create an embryo that initializes a new project and another that generates a source and test file for a new component. When the "new component" embryo runs, it knows how to resolve the name of the project it's in and can therefore generate the correct import statements when rendering its templates.

### Virtual filesystem
A basic embryo will contain two main components: a `tree.yml` file and a `templates` directory. Unlike existing project scaffolding tools, the template files need not be arranged in the filesystem in a way that mirrors the structure defined in the tree file. Instead, you can store all your templates directly in the `templates` directory while tinkering with their arrangement in the tree file.

For example, consider the following embryo, called "project", with the following structure:

*the "project" embryo directory*
```
|- project/
  |- tree.yml
  |- templates/
    |- entity
    |- unit_test
    |- README.md
    |- app.py
    |- setup.py
```

*tree.yml*
```yaml
---
- {{ project_name }}:
  - README.md
  - setup.py
  - {{ project_name|snake }}:
    - app.py
    - entities:
      - account.py: entity(account)
      - user.py: entity(user)
  - test:
    - test_account.py: unit_test(account)
    - test_user.py: unit_test(user)
...
```

Notice how templates are contained in a flat listing in the `templates` directory, and at the same time, some of them are invoked like functions in the `tree.yml` file. The "argument" to these "functions" are top-level properties in the template rendering context (a Python dict). These elements of the context object might contain JSONSchemas used by the `entity` and `unit_test` templates to generate Python class with corresponding getters and setters.

Hatching this embryo with `embryo hatch --project-name AmorphousUnicorn`

would produce the following structure on the filesystem:

```
|- AmorphousUnicorn/
  |- README.md
  |- setup.py
  |- amorphous_unicorn/
    |- app.py
    |- entities/
      |- account.py
      |- user.py
  |- test/:
    |- test_account.py
    |- test_user.py
```

### Composition & Nesting
In addition to utililizing Embryo's self-awareness and virtual filesystem, it is also possible for one embryo to nest other embryos inside the tree file. For example, an embryo that initializes a Git repository within a new project might have a tree file like this:

```yaml
---
- {{ project_name }}:
  - embryo: git(python)
  - {{ project_name|snake }}:
    - app.py
...
```

Notice the nested Git embryo, which is invoked like a function: `git(python)`. In this example, we're assuming that the Git embryo has a static `context.yml` file, containing custom rules for, say, generating the `.gitignore` file for different project types. As a technical note, embryos are built in a breadth-first traversal.

### Code Formatting
Embryo currently supports Yapf as a code formatting engine. Any Python module will be passed through Yapf for formating, so you need not bang your head too hardly against the wall trying to get template files to output the correct Python code structure.
