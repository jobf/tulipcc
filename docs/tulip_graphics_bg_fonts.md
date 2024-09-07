# The Tulip Creative Computer Board

# Customise bg_str fonts 

You can browse available fonts here https://github.com/olikraus/u8g2/wiki/fntlistall

Here's the font files https://github.com/olikraus/u8g2/tree/master/tools/font/build/single_font_files


Then put them in `tulip/shared/u8fontdata.c`. 

And update so that they are properly included in here `tulip/shared/u8g2_fonts.h` and  `tulip/shared/u8g2_fonts.c`

e.g. https://github.com/olikraus/u8g2/blob/d46a3c266924df2517e909f03b1b5f81af9232ac/tools/font/build/single_font_files/u8g2_font_spleen16x32_mu.c

