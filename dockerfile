#Deriving the latest base image
FROM python:latest


#Labels as key value pair
LABEL Maintainer="cookiej4r"


# Any working directory can be chosen as per choice like '/' or '/home' etc
# i have chosen /usr/app/src
WORKDIR /usr/app/src

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

#to COPY the remote file at working directory in container
COPY . .
# Now the structure looks like this '/usr/app/src/test.py'


#CMD instruction should be used to run the software
#contained by your image, along with any arguments.

CMD [ "python", "./src/app.py"]