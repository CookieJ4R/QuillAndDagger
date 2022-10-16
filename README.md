# QuillAndDagger
Quill and Dagger is a server-like software that allows hosting small-scale writing competitions consisting of a 
writing and review phase.

It uses python with the flask framework to serve templated webpages for the individual phases.
Users will need an authentication token to take part in a competition which has to be provided by 
the host (see: [How to use](#how-to-use)).

## How to use:
1. Change the Settings in the WEBSERVER-Section of the 'app_config.ini' to fit your configuration
2. Add your writing prompts to the 'prompts' file
3. Set the STATE_MACHNINE Settings in the 'app_config.ini' file to fot your needs.  
   Useable timezones can be found
   in the available_timezones.txt in the project root.  
   The 'phase_end' config options configure when a specified phase will end. The format used is the iso-format:  
   YYYY-MM-DDTHH:MM:SS   
   'initial_state' describes in which state the application will start:
   
   * 0 = Preparation Phase (default)
   * 1 = Writing Phase
   * 2 = Review Phase
   * 3 = Result Phase
   
4. All users need an authentication token which needs to be generated by the server owner by running uuid_gen.py 
   with the amount of tokens to be generated as an argument (e.g. "python uuid_gen.py 3" for 3 uuids). 
   More UUID tokens can be added later but require an application restart.
   Alternatively, you can use [GUARD](#https://github.com/Baspla/GUARD). For this, follow the instruction provided in the README of the main_GUARD branch.
5. Run app.py with CWD QuillAndDagger (e.g. python src/app.py) and open the specified ip:port in your browser.
   
## Cleanup
After finishing a Quill and Dagger writing competition there are a few files that should be removed.
This can easily be done by running the provided cleanup_qad bash file in the project root.

Please note that this will remove all submissions but will backup them to a zip file into the project root 
before deleting them.
