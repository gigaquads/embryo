# Embryo

## What is an embryo?
Embryo is a program for manipulating the state of the filesystem. _An_ embryo is a directory, containing a handful of files, which specify a tree in the filesystem and templates for generating files. It provides Python hooks for performing custom logic and data transformations along the way. .

### Self-awareness
When files are generated, Embryo stores metadata pertaining to what embryo was run, where the changes were made, and what data was used to render the templates. Each embryo can access metadata dynamically by it in a table, indexed by location in the filesystem.

By taking advantage of stored state, you can write symbiotic embryos, which work with each other. For example, one embryo could initialize a new project while another generates source and test files for a new component. This hypothetical component embryo would know how to discover the name of the host source code package by inspecting metadata and could therefore render the correct import statements in the generated files.
