from __future__ import annotations
from fastmcp import FastMCP

mcp = FastMCP("arith")

def _as_number(x):
    # Accept inits/float or numeric strings; raise clean error otherwise
    if isinstance(x,(int,float)):
        return float(x)
    if isinstance(x, str):
        return float(x.strip())
    
    raise TypeError("expected a number (int/float or numeric string)")

@mcp.tool()
async def add(a: float, b: float) -> float:
    """Return a + b."""
    return _as_number(a) + _as_number(b)

@mcp.tool()
async def subtract(a: float, b: float) -> float:
    """Return a - b."""
    return _as_number(a) - _as_number(b)

@mcp.tool()
async def multiply(a: float, b: float) -> float:
    """Return a * b."""
    return _as_number(a) * _as_number(b)

@mcp.tool()
async def divide(a: float, b: float) -> float:
    """Return a/b. Raises on division bt zero."""
    if b!=0:
        return _as_number(a) / _as_number(b)
    
    raise ValueError("expected a non-zero integer for division")

@mcp.tool()
async def modulus(a: float, b: float) -> float:
    return _as_number(a) % _as_number(b)