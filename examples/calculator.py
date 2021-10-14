# Example by 404kuso
# https://github.com/discord-py-ui/discord-ui/tree/main/examples/calculator.py
#
#       This example will send a working calculator to the text channel with buttons
#
# Note:
#       If you want to test this, replace '785567635802816595' in guild_ids=[] with a guild id of 
#       your choice, because guild slash commands are way faster than globals

import asyncio
from discord.ext import commands
from discord_ui import SlashedCommand, UI, Button
from discord_ui.components import LinkButton

# The main discord bot client
client = commands.Bot(" ")
# Initialize the extension
ui = UI(client)


# A component list for the calculator
calculator = [
    [Button("7", "num_7", "blurple"), Button("8", "num_8", "blurple"), Button("9", "num_9", "blurple"), Button("+", "plu", "green"), Button(")", "close", "green")],
    [Button("4", "num_4", "blurple"), Button("5", "num_5", "blurple"), Button("6", "num_6", "blurple"), Button("-", "sub", "green"), Button("(", "open", "green")],
    [Button("1", "num_1", "blurple"), Button("2", "num_2", "blurple"), Button("3", "num_3", "blurple"), Button("*", "mult", "green"), Button("⌫", "backs", "red")],
    LinkButton("https://github.com/discord-py-ui/discord-ui/tree/main/examples/calculator.py", "ヾ(≧▽≦*) click here for source code ヾ(≧▽≦*)")
]



# Create a slash command
@ui.slash.command(name="calculator", description="opens a calculator, that will automatically close when no input was provided after 20 seconds", guild_ids=[785567635802816595])
async def test(ctx: SlashedCommand):
    # The current query for the calculator
    query = ""
    # Send the calculato, \u200b is an 'empty' char
    msg = await ctx.send("```\n\u200b```", components=calculator)

    # Infinite loop
    while True:
        try:
            # Wait for a button press with a timeout of 20 seconds
            btn = await msg.wait_for("button", client, timeout=20)
            # Respond to the button, that it was received
            await btn.respond(ninja_mode=True)
            # If the button was the equal button
            if btn.custom_id == "equ":
                try:
                    # Execute the current calculation query
                    # Note: Eval is not a safe function, just to say
                    query += "\n= " + str(eval(query))
                # When trying to divide by zero
                except ZeroDivisionError:
                    # Indicate that an error appeared
                    query = "Cannot divide by zero"
            # If the "C" buttont was pressed
            elif btn.custom_id == "cls":
                # Clear the query
                query = ""
            # If the button was the delete button
            elif btn.custom_id == "backs":
                # Remove one character
                query = query[:-1]
            # else
            else:
                # Add the label on the button to the query
                query += btn.label

            # Show the current query, if the query is empty, send the 'empty' character
            await msg.edit(content="```python\n" + (query if query != "" else "\u200b") + "```")
            # If the equal button was pessed
            if btn.custom_id == "equ":
                # clear the query
                query = ""
        # When 20 seconds passed without input (we set the timeout to 20 seconds)
        except asyncio.TimeoutError:
            # Delete the calculator
            await msg.delete()
            # Break out of the inifite loop
            break

# Start the bot, replace 'bot_token_here' with your bot token
client.run("bot_token_here")
