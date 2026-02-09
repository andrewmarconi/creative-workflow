# Minimal makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= uv run sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile text-flat

# Build text output into a flat directory (for LLM/NotebookLM ingestion).
# Flattens hierarchy by replacing path separators with hyphens:
#   developer/api/index.txt → developer-api-index.txt
text-flat:
	@$(SPHINXBUILD) -M text "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@rm -rf "$(BUILDDIR)/text-flat"
	@mkdir -p "$(BUILDDIR)/text-flat"
	@cd "$(BUILDDIR)/text" && find . -name "*.txt" | while read f; do \
		name=$$(echo "$$f" | sed 's|^\./||; s|/|-|g'); \
		cp "$$f" "../text-flat/$$name"; \
	done
	@echo
	@echo "Flat text output in $(BUILDDIR)/text-flat/"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
