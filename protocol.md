# Communication Protocol

Definition of how the PC software and the ESP32 firmware exchange data.
Both sides must implement it exactly as written.

All numeric values must exist as constants in the code (see section 14);

---

## 1. Transport

| Property | Value |
|---|---|
| Medium | Serial (UART). In the Wokwi simulation it is exposed as `rfc2217://localhost:4000` |
| Encoding | UTF-8 text |
| Format | One JSON object per packet |

---

## 2. Packet delimiter

- Every packet is **one line**: a JSON object followed by a single line feed (`\n`, byte `0x0A`).
- A packet **must not** contain a raw newline inside the JSON. `json.dumps(...)` without indentation satisfies this.
- When receiving, strip surrounding whitespace, so a trailing `\r` (`\r\n`) is tolerated.
- Empty lines are ignored.
- Lines that are not valid JSON (for example firmware boot output) are invalid input (see section 8).

Example on the wire (the final `\n` is invisible):

```
{"packet_type": 6, "packet_id": 17, "event_type": 1, "state": 1}
```

---

## 3. Packet structure

Every packet is a JSON object with the following keys.

| name | values | description |
| - | - | - |
| `packet_type` | numeric | Kind of information in this packet (see section 4). Required in every packet |
| `packet_id` | numeric, 0-65535 | Sequential id (see sections 5 and 6). Required in every packet **except** `DECIBLES_UPDATE` and `ERROR`, which have no id |
| `event_type` | numeric | Only in `EVENT` packets (see section 4.1) |
| `state` | numeric, 0 or 1 | Only in `EVENT` packets. `0` = off, `1` = on |
| `decibles` | numeric | Only in `DECIBLES_UPDATE`. Sound level in dB |
| `sound_tresh` | numeric, 0-1 | Only in `SOUND_THRESHOLD_UPDATE`. How sensitive the microphone is to sound |
| `severity` | numeric, 0-100 | Only in `HEARTBEAT_RESPONSE`. See section 4.3 |
| `error_code` | numeric | Only in `ERROR`. See section 8 |
| `message` | string | Optional, only in `ERROR`. Human readable text for logs |
| `suppressed` | numeric | Optional, only in `ERROR`. How many errors were not sent because of the rate limit since the last one |

Key names are kept exactly as above. Unknown extra keys must be ignored by the receiver.

---

## 4. Packet types

| `packet_type` | Name | Direction | Required extra keys | `packet_id` | Needs ACK |
|---|---|---|---|---|---|
| `0` | `ACK` | both | none | received id + 1 | no |
| `1` | `HEARTBEAT` | PC -> ESP | none | sender's next id | answered by `HEARTBEAT_RESPONSE` |
| `2` | `HEARTBEAT_RESPONSE` | ESP -> PC | `severity` | heartbeat id + 1 | no (it is the ACK) |
| `3` | `DECIBLES_UPDATE` | ESP -> PC | `decibles` | none | no (best effort) |
| `4` | `TRIGGER_CAMERA` | PC -> ESP | none | sender's next id | yes |
| `5` | `SOUND_THRESHOLD_UPDATE` | PC -> ESP | `sound_tresh` | sender's next id | yes |
| `6` | `EVENT` | ESP -> PC | `event_type`, `state` | sender's next id | yes |
| `7` | `ERROR` | both | `error_code` | none | no, never |
| `8` | `RESET` | PC -> ESP | none | always `0` | yes (ACK with id `1`) |

Numbers are never reused. New packet types get the next free number.

### 4.1 Event types (`event_type`, used with `EVENT`)

An event reports that something switched on or off. The `state` key says which way.

| `event_type` | Name | `state` `1` means | `state` `0` means |
|---|---|---|---|
| `0` | `CAMERA` | Camera turned on | Camera turned off |
| `1` | `RECORDING` | Recording started | Recording ended |

Rules:
- `state` is required in every `EVENT` and must be `0` or `1`. Anything else is an `INVALID_VALUE` error.
- A receiver acts on **changes** only. If it gets `RECORDING` with `state` `1` while it already knows recording is on, it keeps its state and does nothing more.
- New switchable things get a new `event_type`. If a future event is not an on/off thing, this table must say so.

### 4.2 Packet descriptions and examples

**`ACK` (0)** confirms receipt of a packet. Its `packet_id` is the id of the received packet **plus 1** (wrapping from 65535 to 0). This is the id the sender must use for its next packet.

```json
{"packet_type": 0, "packet_id": 18}
```
(acknowledges the packet with id 17)

**`HEARTBEAT` (1)** is sent by the PC every 5 seconds to check that the ESP is alive.

```json
{"packet_type": 1, "packet_id": 40}
```

**`HEARTBEAT_RESPONSE` (2)** is the ESP's answer. It takes the place of an ACK, so its `packet_id` is the heartbeat's id plus 1. It reports the ESP's health in `severity`.

```json
{"packet_type": 2, "packet_id": 41, "severity": 0}
```

**`DECIBLES_UPDATE` (3)** reports the current sound level. It has no `packet_id` and does not take part in the id sequence.

```json
{"packet_type": 3, "decibles": 62}
```

**`TRIGGER_CAMERA` (4)** tells the ESP to trigger the camera.

```json
{"packet_type": 4, "packet_id": 41}
```

**`SOUND_THRESHOLD_UPDATE` (5)** sets how sensitive the microphone is.

```json
{"packet_type": 5, "packet_id": 42, "sound_tresh": 0.35}
```

**`EVENT` (6)** reports that the camera or the recording switched on or off.

```json
{"packet_type": 6, "packet_id": 17, "event_type": 1, "state": 1}
```
(recording started)

**`ERROR` (7)** reports a problem. It has no `packet_id`, is never acknowledged, and is never answered with another `ERROR`. The receiver does not have to parse it; its main purpose is to show up in logs.

```json
{"packet_type": 7, "error_code": 2, "message": "Missing key: state"}
```

**`RESET` (8)** is sent by the PC to bring a device out of lockdown (see section 9). Its `packet_id` is always `0`.

```json
{"packet_type": 8, "packet_id": 0}
```

### 4.3 Severity levels

`severity` in `HEARTBEAT_RESPONSE` lets the ESP report its health.

| severity | Name | Meaning | Action on the PC |
|---|---|---|---|
| 0 | OK | No errors | none |
| 1-49 | MINOR | Minor problems | log |
| 50-89 | SERIOUS | Serious problems | warn the user |
| 90-99 | CRITICAL | Critical problems | warn the user and stop dependent features |
| 100 | EMERGENCY | Unrecoverable fault | enter the emergency state (section 10) |

---

## 5. Packet ids and acknowledgement process

### 5.1 Two independent sequences

The PC and the ESP each have their own sequence of ids for the packets **they send**. The ESP's ids are unrelated to the PC's ids.

- The first packet a side sends after startup uses id `0`.
- After `65535` the next id is `0` again (wrap-around).

### 5.2 How an acknowledgement works

1. The sender sends a packet with id `N`.
2. The receiver processes it and replies with an `ACK` whose `packet_id` is **`N + 1`**.
3. The sender takes the id from the ACK and **uses it as the id of its next packet**. Normally this equals its own counter + 1.
4. When the receiver later sees a packet with id `N + 1`, it knows its ACK arrived.

Sequence example:

```
PC  -> ESP : {"packet_type": 5, "packet_id": 42, "sound_tresh": 0.35}
ESP -> PC  : {"packet_type": 0, "packet_id": 43}
PC  -> ESP : {"packet_type": 4, "packet_id": 43}      <- next packet reuses the ACK's id
ESP -> PC  : {"packet_type": 0, "packet_id": 44}
```

### 5.3 One packet at a time

Because the next id comes from the ACK, a sender may have **only one unacknowledged packet at a time**. Further packets wait in a queue until the ACK arrives or the retries are used up (section 7).

### 5.4 Rules

1. `ACK` and `ERROR` packets are never acknowledged.
2. `HEARTBEAT` is answered by `HEARTBEAT_RESPONSE`, which has the role of an ACK: its id is the heartbeat id + 1, and no separate `ACK` is sent.
3. `DECIBLES_UPDATE` is best effort. It has no `packet_id`, is not acknowledged and not retransmitted, because a lost reading is replaced by the next one. It does not affect the id sequence.
4. A packet with an unknown `packet_type` is acknowledged (so the sender's sequence can continue) **and** answered with an `ERROR` (section 8), then ignored.
5. An invalid packet (see section 8) is **not** acknowledged. The sender's retry rules (section 7) then apply.
6. If an ACK arrives with an id other than `N + 1` for the packet in flight, the sender ignores it, which counts as a missing ACK.

---

## 6. What the receiver expects

After sending an `ACK` with id `M`, the receiver expects the sender's next packet to have id `M`. It compares the id of each incoming packet (packets without an id are skipped) with `M`:

| Incoming id | Meaning | Action |
|---|---|---|
| `M` | Normal. This also confirms that the ACK arrived | Process the packet |
| `M - 1` (the id just acknowledged) | The sender never received the ACK | **Do not process again** (duplicate). Send the same ACK (`M`) again |
| `0` (when `M` is not `0`) | The sender restarted | Reset the expectation: process the packet and reply with ACK `1` |
| anything else | Unexpected id, packets may be missing | Log it, process the packet, reply with ACK (id + 1) and continue from there |

`M - 1` wraps around the same way: after id `0` was acknowledged with `1`, a repeated `0` is a duplicate.

---

## 7. Packet loss and retries

### 7.1 Detecting loss

- **Lost packet or lost ACK (sender side):** the sender gets no valid ACK within **500 ms**.
- **Lost ACK (receiver side):** the receiver sees the old id `M - 1` again instead of `M` (table in section 6).
- **Lost sound readings:** not detected and not repaired (section 5.4, rule 3).

### 7.2 Retry rules

- On a missing ACK, resend the same packet (same `packet_id`).
- Retry at most **3 times**, 500 ms apart.
- If there is still no ACK after the third retry, the packet is considered failed. The sender logs it, reports a link problem, and continues with the next queued packet using the **same id** (`N`, since no ACK arrived to advance it), so the receiver's expectation stays consistent.

### 7.3 Duplicates

A retry can reach a receiver that already processed the packet (when only the ACK was lost). The receiver recognises it by the rule in section 6, sends the ACK again, and does **not** process the packet a second time.

### 7.4 Restarts

A device that restarts begins again at id `0` and forgets everything in memory: packets waiting for an ACK, its settings, and which ids it has seen.

- The other side recognises the restart by the rule in section 6 (an id of `0` when something else was expected) and resets its expectation.
- Anything that was unacknowledged at the time of the restart is lost.
- After the ESP restarts, the PC should resend the settings the ESP lost (for example `SOUND_THRESHOLD_UPDATE`).

---

## 8. Errors and invalid input

### 8.1 Error codes

| `error_code` | Name | Sent when |
|---|---|---|
| `0` | `INVALID_JSON` | The line is not valid JSON |
| `1` | `NOT_AN_OBJECT` | Valid JSON, but not an object |
| `2` | `MISSING_KEY` | A required key is missing. `message` names the key |
| `3` | `INVALID_VALUE` | A value is out of range or has the wrong type (for example `state` is not 0 or 1) |
| `4` | `UNKNOWN_PACKET_TYPE` | The `packet_type` is not known |
| `5` | `LOCKDOWN` | The sender is in lockdown (section 9) |
| `6` | `EMERGENCY` | The sender is in the emergency state (section 10) |

### 8.2 What happens with each kind of bad input

| Situation | ACK? | Error sent |
|---|---|---|
| Line is not valid JSON | no | `INVALID_JSON` |
| Valid JSON but not an object | no | `NOT_AN_OBJECT` |
| Missing `packet_type`, or missing `packet_id` (where one is required) | no | `MISSING_KEY` |
| Unknown `packet_type` | **yes** (id + 1) | `UNKNOWN_PACKET_TYPE` |
| Required extra key missing (for example `state` in an `EVENT`) | no | `MISSING_KEY` |
| Value invalid (for example `state` is 2) | no | `INVALID_VALUE` |
| Input stream closed (empty read) | n/a | `message`: "Input closed"; the ESP stops listening (current firmware behaviour) |

Because an invalid packet gets no ACK, the sender retries it up to 3 times (section 7.2), and the receiver may therefore send up to 3 errors for it. That is intended: it makes the problem obvious in the log.

### 8.3 Rules for errors

1. **Never answer an `ERROR` with an `ERROR`.** Otherwise two devices could bounce errors back and forth forever.
2. **`ERROR` and `DECIBLES_UPDATE` have no `packet_id`.** They are exempt from the "missing `packet_id`" check.
3. **The ESP reports every case in section 8.2** to the PC.
4. **The PC logs every case in section 8.2 locally.** It sends an `ERROR` back only for lines that are valid JSON objects with a problem. It does not send `INVALID_JSON` errors for non-JSON lines, because the ESP also prints boot and debug text on the same line, and answering that would flood the ESP.
5. **Rate limit:** a side sends at most one `ERROR` per second. Errors that are dropped by the limit are counted and reported in the `suppressed` key of the next one. Emergency repeats (section 10) are exempt.
6. The receiver of an `ERROR` does not have to parse it. Writing it to the log or counting it is enough.

---

## 9. Lockdown

Lockdown means the connection is no longer trustworthy. Something has gone wrong, and packets or settings may have been lost in a way the protocol cannot repair.

### 9.1 Entering lockdown

- **PC:** 3 consecutive `HEARTBEAT` packets get no `HEARTBEAT_RESPONSE` (15 seconds).
- **ESP:** no valid packet from the PC for 15 seconds.
- In both cases the timer only starts after the **first valid packet** has been received. Before that, a side simply waits (the PC keeps sending heartbeats and shows "waiting for device").

### 9.2 Behaviour in lockdown

- The locked device **only answers with `ERROR`** (`error_code` `LOCKDOWN`), whatever packet it receives. It sends no ACKs, no heartbeats, no events and no sound updates. The rate limit and the "never answer an error" rule still apply.
- **ESP safe state:** stop recording and switch the camera off.
- **PC:** stop sending heartbeats, discard the send queue, and show a clear warning.
- A valid packet does **not** clear lockdown.

### 9.3 Leaving lockdown

- **ESP:** only a `RESET` packet from the PC, or a restart of the ESP, ends lockdown. On `RESET` the ESP sets its own next id to `0`, expects the PC's next id to be `1`, replies `ACK` with `packet_id` `1`, and resumes normal operation.
- **PC:** only user action ends lockdown (restarting the program, or a "reconnect" action). The PC then sends `RESET`. When the ACK arrives, the PC expects the ESP's next id to be `0`.
- The PC should resend the ESP's settings after a reset (for example `SOUND_THRESHOLD_UPDATE`), because the ESP may have lost them.

`RESET` is ignored in the emergency state.

---

## 10. Emergency state

The emergency state is for a fault that is unconditional and unrecoverable. Either side can signal it. It is not expected to happen in normal use.

### 10.1 Triggering

- **ESP:** reports `severity` `100` in a `HEARTBEAT_RESPONSE`, or sends an `ERROR` with `error_code` `EMERGENCY` (immediately, without waiting for the next heartbeat).
- **PC:** sends an `ERROR` with `error_code` `EMERGENCY` (for example from an emergency-stop control).

### 10.2 Behaviour

1. **The receiver enters the emergency state too.** Both sides end up shut down.
2. **Everything shuts down:** camera, recording, buzzer, LED bar and indicators go off, outputs are set to a safe state, queued packets are discarded, and no new work starts.
3. **Nothing can clear it.** No packet, including `RESET`, ends the emergency state. Only a physical restart (power cycle, or closing and reopening the program) does.
4. A side in the emergency state only repeats `ERROR` with `error_code` `EMERGENCY`, once per second. It does not wait for an ACK, and receivers do not reply.
5. The emergency state overrides lockdown, the ACK rules, the retry logic and the send queue.

### 10.3 The three states

| State | Trigger | How it ends |
|---|---|---|
| Normal | | |
| Lockdown | Connection lost (section 9.1) | `RESET` packet or restart |
| Emergency | Severity `100` or an `EMERGENCY` error | Physical restart only |

---

## 11. Timing summary

| Value | Setting |
|---|---|
| Heartbeat interval | 5 s |
| ACK timeout | 500 ms |
| Max retries | 3 |
| Missed heartbeats before lockdown | 3 |
| Lockdown after silence | 15 s |
| Minimum interval between `ERROR` packets | 1 s |
| Emergency repeat interval | 1 s |

---

## 12. Example sessions

**Normal exchange**

```
PC  -> ESP : {"packet_type": 1, "packet_id": 40}
ESP -> PC  : {"packet_type": 2, "packet_id": 41, "severity": 0}

ESP -> PC  : {"packet_type": 3, "decibles": 62}

PC  -> ESP : {"packet_type": 4, "packet_id": 41}
ESP -> PC  : {"packet_type": 0, "packet_id": 42}

ESP -> PC  : {"packet_type": 6, "packet_id": 17, "event_type": 1, "state": 1}
PC  -> ESP : {"packet_type": 0, "packet_id": 18}
```

**Lost packet**

```
ESP -> PC  : {"packet_type": 6, "packet_id": 17, "event_type": 1, "state": 1}   (lost)
             ... 500 ms, no ACK ...
ESP -> PC  : {"packet_type": 6, "packet_id": 17, "event_type": 1, "state": 1}   (retry, same id)
PC  -> ESP : {"packet_type": 0, "packet_id": 18}
```

**Lost ACK**

```
PC  -> ESP : {"packet_type": 4, "packet_id": 41}
ESP -> PC  : {"packet_type": 0, "packet_id": 42}                       (ACK lost)
             ... 500 ms, no ACK ...
PC  -> ESP : {"packet_type": 4, "packet_id": 41}                       (retry)
             ESP expected 42 but sees 41: duplicate, camera is NOT triggered twice
ESP -> PC  : {"packet_type": 0, "packet_id": 42}                       (ACK sent again)
PC  -> ESP : {"packet_type": 5, "packet_id": 42, "sound_tresh": 0.5}   (next packet reuses 42)
```

**Invalid input**

```
PC  -> ESP : {"packet_type": 6, "packet_id": 42, "event_type": 1}      (state missing)
ESP -> PC  : {"packet_type": 7, "error_code": 2, "message": "Missing key: state"}
             ... no ACK, so the PC retries ...
```

**Unknown packet type**

```
PC  -> ESP : {"packet_type": 99, "packet_id": 42}
ESP -> PC  : {"packet_type": 0, "packet_id": 43}
ESP -> PC  : {"packet_type": 7, "error_code": 4, "message": "Unknown packet type 99"}
```

**Lockdown and reset**

```
             (ESP gets no packet from the PC for 15 s and locks)
PC  -> ESP : {"packet_type": 1, "packet_id": 50}
ESP -> PC  : {"packet_type": 7, "error_code": 5, "message": "Locked"}
             (user reconnects the PC)
PC  -> ESP : {"packet_type": 8, "packet_id": 0}
ESP -> PC  : {"packet_type": 0, "packet_id": 1}
PC  -> ESP : {"packet_type": 5, "packet_id": 1, "sound_tresh": 0.35}   (settings resent)
```

**Emergency**

```
ESP -> PC  : {"packet_type": 7, "error_code": 6, "message": "Emergency stop"}
             (both sides shut everything down; the ESP repeats the packet every second)
PC  -> ESP : {"packet_type": 8, "packet_id": 0}                        (ignored)
```

---

## 14. Constants

Define these once, in one file shared by the PC and the ESP, so the numbers exist in a single place. Each category is a plain class (MicroPython has no `enum` module). Code uses them as `PacketType.EVENT`, `Timing.MAX_RETRIES`, and so on.

```python
# protocol_constants.py

class PacketType:
    ACK = 0
    HEARTBEAT = 1
    HEARTBEAT_RESPONSE = 2
    DECIBLES_UPDATE = 3
    TRIGGER_CAMERA = 4
    SOUND_THRESHOLD_UPDATE = 5
    EVENT = 6
    ERROR = 7
    RESET = 8

class EventType:
    CAMERA = 0
    RECORDING = 1

class State:
    OFF = 0
    ON = 1

class ErrorCode:
    INVALID_JSON = 0
    NOT_AN_OBJECT = 1
    MISSING_KEY = 2
    INVALID_VALUE = 3
    UNKNOWN_PACKET_TYPE = 4
    LOCKDOWN = 5
    EMERGENCY = 6

class Severity:  # lowest value of each band
    OK = 0
    MINOR = 1
    SERIOUS = 50
    CRITICAL = 90
    EMERGENCY = 100

class Timing:
    HEARTBEAT_INTERVAL_S = 5
    ACK_TIMEOUT_S = 0.5
    MAX_RETRIES = 3
    MISSED_HEARTBEATS_LIMIT = 3
    LOCKDOWN_TIMEOUT_S = 15
    ERROR_MIN_INTERVAL_S = 1
    EMERGENCY_REPEAT_S = 1
    PACKET_ID_MODULO = 65536


def next_id(packet_id):
    return (packet_id + 1) % Timing.PACKET_ID_MODULO


def name_of(cls, value):
    """Turn a number back into its name for log messages."""
    for name in dir(cls):
        if not name.startswith("_") and getattr(cls, name) == value:
            return name
    return str(value)

# name_of(PacketType, 6) -> "EVENT"
```

---