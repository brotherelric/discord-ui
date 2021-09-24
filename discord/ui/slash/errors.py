class AlreadyDeferred(Exception):
    """Exception that is raised when you try to defer an interaction that was already deferred."""
    def __init__(self, *args: object) -> None:
        super().__init__("Interaction was already deferred")
class EphemeralDeletion(Exception):
    """Exception that is raised when you try to delete an ephemeral message.
    
    Ephemeral messages can not be deleted"""
    def __init__(self, *args: object) -> None:
        super().__init__("Cannot delete an ephemeral message")
class MissingOptionParameter(Exception):
    """Exception that is raised when a callback is missing a parameter which was 
    specified in the slash command.
    
    If you have a slashcommand with ``role`` as the name, your callback has to 
    accept a parameter with the name ``role``.

    For example
    
    .. code-block::

        @ui.slash.command(..., options=[SlashOption(SomeType, role, required=True)])
        async def callback(ctx, role):      # role is the name of the option
            ...
    """
    def __init__(self, option_name, *args: object) -> None:
        super().__init__("Missing parameter '" + option_name + "' in callback function")
class OptionalOptionParameter(Exception):
    """Exception that is rarised when a callback function has a required parameter which 
    is marked optional in the slash command.
    
    If you want to have an optional option in your callback, you need to specify a default value 
    for it: ``async def callback(ctx, my_option=None)``
    """
    def __init__(self, param_name, *args: object) -> None:
        super().__init__("Parameter '" + param_name + "' in callback function needs to be optional (" + param_name + "=None)")
class NoAsyncCallback(Exception):
    """Exception that is raised when a sync callback was provided
    
    Callbacks have to be async
    """
    def __init__(self, *args: object) -> None:
        super().__init__("callback has to be async")
class CallbackMissingContextCommandParameters(Exception):
    """Exception that is raised when a callback for a context command is missing parmeters.
    
    A context-command callback has to accept two parameters, one for the interaction context
    and the other one for the passed parameter.
    """
    def __init__(self, *args: object) -> None:
        super().__init__("Callback function for context commands has to accept 2 parameters (the used command, the message/user on which the interaction was used)")
