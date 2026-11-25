# Communication Protocol

definition of how the PC software and the ESP32 firmware exchange data. (Both sides must implement it exactly as written) 

The numeric values in section 4 must also exist as constants in the code (see section 12).

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
- A packet must not contain a raw newline inside the JSON. `json.dumps(...)` without indentation satisfies this.
- Empty lines are ignored.
- Lines that are not valid JSON are treated as invalid packets (see section 8).

Example (the final \n is invisible):

```
{"packet_type": 3, "packet_id": 17, "decibles": 62}
```

---

## 3. Packet structure

Every packet is a JSON object with the following keys.

| name | values | description |
| - | - | - |
| `packet_type` | numeric | Kind of information in this packet (see section 4). Required in every packet |
| `packet_id` | numeric, 0-65535 | Sequential id, used for acknowledgements and loss detection (see sections 5 and 7). Required in every packet |
| `event_type` | numeric | Only present in `EVENT` packets (see section 4.1) |
| `decibles` | numeric | Only present in `DECIBLES_UPDATE`. Sound level in dB |
| `sound_tresh` | numeric, 0-1 | Only present in `SOUND_THRESHOLD_UPDATE`. How sensitive the microphone is to sound |
| `severity` | numeric, 0-100 | Only present in `HEARTBEAT_RESPONSE`. 0 = no errors, 100 = highest severity (critical) |

Key names are kept exactly as above. Unknown extra keys must be ignored by the receiver.

---

## 4. Packet types

| `packet_type` | Name | Direction | Required extra keys | Needs ACK |
|---|---|---|---|---|
| `0` | `ACK` | both | none | no |
| `1` | `HEARTBEAT` | PC -> ESP | none | answered by `HEARTBEAT_RESPONSE` |
| `2` | `HEARTBEAT_RESPONSE` | ESP -> PC | `severity` | no |
| `3` | `DECIBLES_UPDATE` | ESP -> PC | `decibles` | no (best effort) |
| `4` | `TRIGGER_CAMERA` | PC -> ESP | none | yes |
| `5` | `SOUND_THRESHOLD_UPDATE` | PC -> ESP | `sound_tresh` | yes |
| `6` | `EVENT` | ESP -> PC | `event_type` | yes |

Numbers are never reused. New packet types get the next free number.

### 4.1 Event types (`event_type`, used with `EVENT`)

| `event_type` | Name | Meaning |
|---|---|---|
| `0` | `CAMERA_ACTIVATED` | Camera turned on |
| `1` | `CAMERA_DEACTIVATED` | Camera turned off |
| `2` | `RECORDING_STARTED` | Recording began |
| `3` | `RECORDING_ENDED` | Recording ended |

### 4.2 Packet descriptions and examples

**`ACK` (0)** confirms receipt of a packet. Its `packet_id` is the id of the packet being acknowledged, not a new id.

```json
{"packet_type": 0, "packet_id": 17}
```

**`HEARTBEAT` (1)** is sent by the PC every 5 seconds to check that the ESP is alive.

```json
{"packet_type": 1, "packet_id": 40}
```

**`HEARTBEAT_RESPONSE` (2)** is the ESP's answer. It reuses the `packet_id` of the heartbeat it answers and reports its health in `severity`. It takes the place of an ACK.

```json
{"packet_type": 2, "packet_id": 40, "severity": 0}
```

**`DECIBLES_UPDATE` (3)** reports the current sound level.

```json
{"packet_type": 3, "packet_id": 17, "decibles": 62}
```

**`TRIGGER_CAMERA` (4)** tells the ESP to trigger the camera.

```json
{"packet_type": 4, "packet_id": 41}
```

**`SOUND_THRESHOLD_UPDATE` (5)** sets how sensitive the microphone is.

```json
{"packet_type": 5, "packet_id": 42, "sound_tresh": 0.35}
```

**`EVENT` (6)** reports that something happened on the device.

```json
{"packet_type": 6, "packet_id": 18, "event_type": 2}
```

---

## 5. Acknowledgement process

1. Each side numbers the packets **it sends** with its own counter (see section 6). The ESP's ids and the PC's ids are independent.
2. When a side receives a valid packet that needs an ACK (see the "Needs ACK" column), it immediately replies with an `ACK` whose `packet_id` is the id of the received packet.
3. `ACK needing` packets are never acknowledged themselves.
4. `HEARTBEAT` is answered by `HEARTBEAT_RESPONSE` with the same `packet_id`; no separate `ACK` is sent.
5. `DECIBLES_UPDATE` is best effort. It is not acknowledged and not retransmitted, because a lost reading is replaced by the next one.
6. A packet with an unknown `packet_type` is acknowledged (so the sender stops retrying) and then ignored.
7. A packet that is invalid (invalid JSON, missing `packet_type` or `packet_id`) is **not** acknowledged. The sender's retry rules (section 7) then apply.

Sequence example:

```
PC  -> ESP : {"packet_type": 5, "packet_id": 42, "sound_tresh": 0.35}
ESP -> PC  : {"packet_type": 0, "packet_id": 42}

ESP -> PC  : {"packet_type": 6, "packet_id": 18, "event_type": 2}
PC  -> ESP : {"packet_type": 0, "packet_id": 18}
```

---

## 6. Packet ids (weak part with packet loss/restarts)

- The first packet a side sends after startup uses `packet_id` `0`.
- Each following packet increases the id by 1.
- After `65535` the next id is `0` again (wraps around).
- A retransmission (section 7) reuses the **original** `packet_id`.
- After a restart a side starts again at `0`. The other side must treat an unexpected jump back to `0` as a restart, not as packet loss.

---

## 7. Packet loss and retries

### 7.1 Detecting loss

Loss is detected in two ways:

1. **Missing ACK:** the sender does not receive the ACK within **500 ms**.
2. **Gap in ids:** the receiver gets an id that is not the previous id + 1 (ignoring wrap-around and restarts). It logs the gap. This is the only loss detection for `DECIBLES_UPDATE`.

### 7.2 Retry rules

- On a missing ACK, resend the same packet (same `packet_id`).
- Retry at most **3 times**, 500 ms apart.
- If there is still no ACK after the third retry, the packet is considered failed. The sender logs it and reports a link problem.

### 7.3 Duplicates

Because of retries, a packet can arrive twice. If a receiver sees an id it has already processed, it sends the ACK again but does **not** process the packet a second time.

### 7.4 Connection lost

- The PC sends a `HEARTBEAT` every 5 seconds.
- If **3 consecutive heartbeats** get no `HEARTBEAT_RESPONSE` (15 seconds), the PC treats the connection as lost and shows a warning.
- The ESP also treats the connection as lost if it receives no packet from the PC for 15 seconds.
- Any received valid packet clears the "lost" state.

### 7.4.1 Severity

`severity` in `HEARTBEAT_RESPONSE` lets the ESP report problems. Suggested handling on the PC:

| severity | Meaning | Action |
|---|---|---|
| 0 | No errors | none |
| 1-49 | Minor problems | log |
| 50-99 | Serious problems | warn the user |
| 100 | Critical | warn the user and stop dependent features |

---

## 8. Errors and invalid input

| Situation | Behaviour |
|---|---|
| Line is not valid JSON | Ignore it. The ESP may reply `{"error": "Invalid JSON"}` (current firmware does) |
| Valid JSON but not an object | Treat as invalid, do not ACK |
| Missing `packet_type` or `packet_id` | Treat as invalid, do not ACK |
| Unknown `packet_type` | ACK, then ignore |
| Required extra key missing (for example `event_type` in an `EVENT`) | Do not process; reply `{"error": "Missing key: <name>"}` |
| Input stream closed (empty read) | ESP sends `{"error": "Something is not good"}` and stops listening (current firmware behaviour) |

Error objects have no `packet_type`. They are recognised by the `error` key and are not acknowledged.

---

## 9. Timing summary

| Value | Setting |
|---|---|
| Heartbeat interval | 5 s |
| ACK timeout | 500 ms |
| Max retries | 3 |
| Connection lost after | 15 s without a valid packet |

---

## 10. Constants

Define these once per side so the numbers are never written as literals.

```python
# protocol_constants.py (use plain integers; MicroPython has no full enum module)

# packet_type
PACKET_ACK = 0
PACKET_HEARTBEAT = 1
PACKET_HEARTBEAT_RESPONSE = 2
PACKET_DECIBLES_UPDATE = 3
PACKET_TRIGGER_CAMERA = 4
PACKET_SOUND_THRESHOLD_UPDATE = 5
PACKET_EVENT = 6

# event_type
EVENT_CAMERA_ACTIVATED = 0
EVENT_CAMERA_DEACTIVATED = 1
EVENT_RECORDING_STARTED = 2
EVENT_RECORDING_ENDED = 3

# timing
HEARTBEAT_INTERVAL_S = 5
ACK_TIMEOUT_S = 0.5
MAX_RETRIES = 3
CONNECTION_TIMEOUT_S = 15
PACKET_ID_MODULO = 65536
```

---

## 11. Example session

```
PC  -> ESP : {"packet_type": 1, "packet_id": 40}
ESP -> PC  : {"packet_type": 2, "packet_id": 40, "severity": 0}

ESP -> PC  : {"packet_type": 3, "packet_id": 17, "decibles": 62}

PC  -> ESP : {"packet_type": 4, "packet_id": 41}
ESP -> PC  : {"packet_type": 0, "packet_id": 41}

ESP -> PC  : {"packet_type": 6, "packet_id": 18, "event_type": 2}
(no ACK arrives within 500 ms)
ESP -> PC  : {"packet_type": 6, "packet_id": 18, "event_type": 2}   <- retry, same id
PC  -> ESP : {"packet_type": 0, "packet_id": 18}
```

---