NODE := node

.PHONY: check demo artifact clean

check:
	@$(NODE) tests/test-cap.js
	@echo ""
	@$(NODE) tests/test-artifact.js

# Regenerate the page from the kernels (a second copy cannot exist).
artifact:
	@$(NODE) tools/build-artifact.js

# Reproduce the headline numbers printed in the README.
demo:
	@$(NODE) tools/report.js

clean:
	@rm -f *.tmp
