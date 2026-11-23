# Networking documentation


## Abstract

The hardware (esp32) and the server (what runs on the computer) communicate through a serial connection. Wokwi is nice enough to provide us with access to the esp32s serial port by mapping it to an rfc2217 complient networking socket. How nice of them.

## Hardware

On the hardware side, the serial port is mapped directly to stdin/out of the micropython script, meaning one can use `input()` for reading serial and `print()` for writing serial data. While `input()` is very convenient, it doesn't play nicely with the asynchrounous nature of our project. That's why we use `asyncio.StreamReader` to read directly from sys.stdin.
This is perfect for our case, since asyncio.StreamReader can read the input (guess what?) **asynchronously 🥳**.

### Reading Incoming Packets

We use a callback-based message routing. Each message has (as described in the protocol documentation) a field for a `packet_type`.

Every request needs that, every request has that.

When you want to listen for a specific packet_type, you have to create a handler. What does a Handler look like? Take a look at the `Handler` type in `networking.py`:

```py
Callable[[dict], Awaitable[dict | None]]
```

now, this does look scary, but it is actually not that complicated.
all this says is that the handler needs to take one argument, a dictionary, and it can return either nothing (so, just `return`) or a dictionary (so, `return { something: value }`)
However, the function needs to be asyncronous (so, defined with `async def function_name()`)

Then you just call the `register_handler()` function from the networking module.
It takes two arguments: The first one is the packet type you would like to listen to. The second one is the handler we just discussed.

> [!Note]
> If a handler gets registered for a packet_type which already has a listener, it will **replace** the existing listener. (This might change, but I couldn't figure out how do deal with the return values so either suggest a way of implementing this or deal with it I guess)

### Sending (writing) Outgoing Packets

> to be continued

## Software (server side)

> to be continued

### Reading Incoming Packets

> to be continued

### Sending (writing) Outgoing Packets

> to be continued
