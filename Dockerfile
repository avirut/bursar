FROM mambaorg/micromamba:1.4.9 as micromamba

ENV IS_DOCKER true

WORKDIR /app

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml environment.yml
RUN micromamba install -y -n base -f environment.yml && \
    micromamba clean --all --yes

COPY src src

# ENTRYPOINT [ "python src/setup.py && python src/run_scheduled.py" ]