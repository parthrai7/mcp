# demo_tools.py
from typing import Any
import random

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("demo-tools")

# --------------------------------------------------
# 1) Echo -------------------------------------------------
# --------------------------------------------------
@mcp.tool()
async def echo(message: str) -> str:
    """Return the exact message you send in."""
    return message

# --------------------------------------------------
# 2) Add -----------------------------------------------
# --------------------------------------------------
@mcp.tool()
async def add(a: float, b: float) -> str:
    """Add two numbers and return the sum as a string."""
    return f"{a} + {b} = {a + b}"

# --------------------------------------------------
# 3) Dice Roll -----------------------------------------
# --------------------------------------------------
@mcp.tool()
async def dice_roll(sides: int = 6) -> str:
    """Roll an n‑sided die (default 6) and return the result."""
    result = random.randint(1, sides)
    return f"🎲 Rolled a {sides}-sided die: {result}"

# --------------------------------------------------
# 4) Temperature Converter ---------------------------
# --------------------------------------------------
@mcp.tool()
async def convert_temperature(value: float, unit: str) -> str:
    """Convert between Celsius and Fahrenheit.

    Args:
        value: the numeric temperature
        unit:  'C' if value is Celsius, 'F' if value is Fahrenheit
    """
    unit = unit.strip().upper()
    if unit == "C":
        f = value * 9 / 5 + 32
        return f"{value:.2f} °C is {f:.2f} °F"
    elif unit == "F":
        c = (value - 32) * 5 / 9
        return f"{value:.2f} °F is {c:.2f} °C"
    else:
        return "Unit must be 'C' or 'F'."

# --------------------------------------------------
# 5) Word Counter -------------------------------------
# --------------------------------------------------
@mcp.tool()
async def word_count(text: str) -> str:
    """Return how many words are in the provided text."""
    count = len(text.split())
    return f"The text contains {count} word{'s' if count != 1 else ''}."

# --------------------------------------------------
# Run the server over stdio so your client can connect
# --------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
