void time_bp() {
  /******************************************************************时间播报***************************************************************************/
  //时播报
  //0x:xx
  if (hour_high == 0 && flag_time_bp == 1) {
    bofang(11);
    delay(2200);
    bofang(hour_low);
    delay(450);
    bofang(12);
    delay(450);
    flag_time_bp = 2;
  }

  //1x:xx
  if (hour_high != 0 && flag_time_bp == 1) {
    if (hour_high != 1) {
      bofang(11);
      delay(2200);
      bofang(hour_high);
      delay(450);
      bofang(10);
      delay(450);
      bofang(hour_low);
      delay(450);
      bofang(12);
      delay(450);
      flag_time_bp = 2;
    }
    else if (hour_high == 1) {
      bofang(11);
      delay(2200);
      bofang(10);
      delay(450);
      bofang(hour_low);
      delay(450);
      bofang(12);
      delay(450);
      flag_time_bp = 2;
    }
  }


  //分播报
  //xx:01
  if (minute_high == 0 && minute_low != 0 && flag_time_bp == 2) {
    bofang(15);
    delay(450);
    bofang(minute_low);
    delay(450);
    bofang(14);
    delay(450);
    flag_time_bp = 3;
  }
  //xx:00
  if (minute_high == 0 && minute_low == 0 && flag_time_bp == 2) {
    bofang(13);
    delay(450);
    flag_time_bp = 3;
  }
  //xx:1x
  if (minute_high != 0 && flag_time_bp == 2) {
    if (minute_high != 1) {
      bofang(minute_high);
      delay(450);
      bofang(10);
      delay(450);
      bofang(minute_low);
      delay(450);
      bofang(14);
      delay(450);
      flag_time_bp = 3;
    }
    else  if (minute_high == 1) {
      bofang(10);
      delay(450);
      bofang(minute_low);
      delay(450);
      bofang(14);
      delay(450);
      flag_time_bp = 3;
    }
  }
}
