# Communication Protocol

Json object with the following keys:

| name | values | description |
| - | - | - |
| packet_type | numeric field | Describes the kind of information that is sent by this packet (decibles update, trigger camera push, sound threshold update, heartbeat, events, acknowledgement)
| packet_id | numeric value | sequential id, used for acknoledgements |
| event_type | numeric field | Only present in one of the event types (camera activated, camera deactivated, recording started, recording ended) |
| decibles | numeric field | Present if packet_type is decibles update. Indicates sound level in dB |
| sound_tresh | numeric field | 0-1 value, how senstive the microphone is to sound
| severity | numeric 0 - 100 | transmitted only with heartbeat responses, 0 is no errors, 100 is a high severity, mega ultra critical death
