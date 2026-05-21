# Stage 1: Use Python 3.10 built specifically for Bookworm (to match Jenkins LTS)
FROM python:3.10-slim-bookworm AS python-base

# Stage 2: Jenkins image
FROM jenkins/jenkins:lts

USER root

# Copy the Python 3.10 binaries and standard libraries
# Using the bookworm-slim base ensures libssl.so.3 matches
COPY --from=python-base /usr/local /usr/local

# Refresh the library cache so the system finds the new Python libs
RUN ldconfig && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    # Add any missing runtime dependencies if needed
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Switch back to the jenkins user
USER jenkins