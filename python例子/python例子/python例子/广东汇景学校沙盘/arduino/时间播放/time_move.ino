void clk_() {
  if (millis() - timeout >= 1000) {
    second_++;
    timeout = millis();
  }
  if (second_ > 59) {
    minute_++; second_ = 0;
  }
  if (minute_ > 59) {
    hour_++; minute_ = 0;
  }
  if (hour_ > 23) {
    day_++;hour_ = 0;
  }
}
