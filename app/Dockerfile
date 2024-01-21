FROM ghcr.io/isaacsancheza/selenium:es-MX

ARG WORKDIR=/app

# install pipenv
RUN pip --disable-pip-version-check --no-cache-dir install pipenv

# create project dir  
RUN mkdir $WORKDIR

# copy files
COPY . $WORKDIR

# change current working dir to project dir
WORKDIR $WORKDIR

# install project deps
RUN pipenv install --system --deploy --ignore-pipfile

# own files
RUN chown -R $USERNAME:$USERNAME $WORKDIR

# run script
CMD [ "/usr/local/bin/python3", "/app/script.py" ]
