import tkinter.filedialog as tkFileDialog
import tkinter as tk
import math
from PIL import Image
def choosefile(FT):
        openerdialog = tkFileDialog.Open(filetypes=FT)
        filename = openerdialog.show(initialdir=dir)
        return filename
def choosesavefile(FT):
    openerdialog = tkFileDialog.SaveAs(filetypes=FT)
    filename = openerdialog.show(initialdir=dir)
    return filename
def format_bytecount(i):
    if i < 1000:
        return(str(i) + "B")
    i /= 1000
    if i < 1000:
        return(str(int(i*10)/10) + "K")
    i /= 1000
    if i < 1000:
        return(str(int(i*10)/10) + "M")
    i /= 1000
    return(str(int(i*10)/10) + "G")
def color_bit_mapping(X,B):
    return int(3*(X%B)/B)
def bit_within_color(X,B):
    #This will only be called if we're recursing. Make it kick out 0.
    X = X % B
    if X == B-1:
        return 0
    if color_bit_mapping(X,B) == color_bit_mapping(X+1,B):
        return bit_within_color(X+1,B) + 1
    return 0
def encode_into_image(bit_depth,bytes_to_encode,img):
    #Which bit we are on in our encodable bytes
    encoder_index = 0
    pixel_count = 0
    for row in range(h):
        for px in range(w):
            pixel_count += 1
            pixel_initial_value = img.getpixel((px,row))
            pixel_final_value = [0,0,0]
            #Iterate over our 3 colors (RGB)
            for j in range(3):
                bits_on_this_color = (bit_depth - j-1)//3 + 1
                byte_to_mod = pixel_initial_value[j]
                if bits_on_this_color != 0:
                    #Drop the proper number of bits off the right of the byte
                    byte_to_mod = byte_to_mod >> bits_on_this_color
                    #Cycle as many times as we need to encode bits.
                    for i in range(bits_on_this_color):
                        byte_with_next_bit = bytes_to_encode[encoder_index//8]
                        next_bit = (byte_with_next_bit & (1 << (encoder_index%8)))!=0
                        #Bump a byte from the pixel over, leaving room in the zero bit to add our next bit
                        byte_to_mod = byte_to_mod << 1
                        byte_to_mod += next_bit
                        encoder_index+=1
                        if encoder_index//8 >= len(encodable_bytes):
                            return img
                pixel_final_value[j] = byte_to_mod
            img.putpixel((px,row),tuple(pixel_final_value))
def find_header(img):
    #Iterate over potential bit depths
    for b in range(1,13):
        header_attempt = extract_bytes(8,img,b,strip_header=False)
        #Now we've extracted 8 bytes with a guess of bit depth.
        #Test if we were right by looking for the 5th byte (0,1,2,3,**4**) to have the magic 1011 sequence.
        #This should be replaced with a proper checksum but... eh.
        if header_attempt[4] >> 4 == 0b1011:
            file_extension = "".join([chr(x) for x in header_attempt[-3:]])
            if all([c in "abcdefghijklmnopqrstuvwxyz" for c in file_extension]):
                print("***")
                print(b)
                print("Possible hidden file header detected. File extension:" + file_extension)
                header_right = input("Press Y if this looks like a valid file extension, or N if we should check for other headers.")
                if header_right.upper() == "Y":
                    return header_attempt
    print("PROBLEM!")
    kill=6/0
def extract_bytes(bytecount,image,bit_depth,strip_header = True):
        w,h=image.size
        bytes_extracted = [0]*bytecount
        for x in range(bytecount * 8):
            pixel_count_to_pull_from = x // bit_depth
            #print("pulling from px" + str(pixel_count_to_pull_from))
            #print("on byte" + str(x//8))
            #print("bit" + str(x%8))
            #Take that pixel count and convert to x,y coords
            x_val = pixel_count_to_pull_from % w
            y_val = pixel_count_to_pull_from // w
            the_pixel = image.getpixel((x_val,y_val))
            #find the right bit corresponding to this x value
            the_color = color_bit_mapping(x,bit_depth)
            bits_on_this_color = (bit_depth - the_color-1)//3 + 1
            the_bit = bit_within_color(x,bit_depth)
            bit_value = the_pixel[the_color] & (1 << the_bit)!=0
            byte_to_add_to = bytes_extracted[x//8]
            #Take the bit value we got out of the image and put it in its place.
            #Note that when we wrote to the header in the encoder, we would grab
            #bits using next_bit = (byte_with_next_bit & (1 << (encoder_index%8)))!=0
            #therefore we decode with the same x%8.
            byte_to_add_to |= bit_value << (x % 8)
            bytes_extracted[x//8] = byte_to_add_to
        if not strip_header:
            return bytes_extracted
        return bytes_extracted[8:]
root = tk.Tk()
root.withdraw()
mode = input("Encode or decode? Press E or D and hit enter.\n")
if mode.upper() == "E":
    input("At the following prompt, choose the image you want to encode into. {ENTER}")
    img = Image.open(choosefile([("Images", "*.png *.jpg"),]))
    w,h=img.size
    pixel_count = w * h
    print(f"Your image has {pixel_count} pixels.")
    for i in range(13):
        print(f"If you use {i} bits per pixel, you will get {format_bytecount(i*pixel_count/8)} encodable storage")
    bit_depth = int(input("How many bits per pixel do you want to use for data?"))
    total_allowed_bytes = pixel_count * bit_depth - 8
    input("At the following prompt, choose the file you want to embed. {ENTER}")
    embed_filename = choosefile([("All files", "*.*"),])    
    with open(embed_filename,'rb') as f:
        embedded_bytes = f.read()
    print(len(embedded_bytes))
    if len(embedded_bytes) > total_allowed_bytes:
        print("Sorry, but we don't have room for that file.")
        kill = 1/0
    file_size_array = [len(embedded_bytes) >> i & 0xff for i in (24,16,8,0)]
    #Bit depth maxes out at 12, which is 4 bits. So take upper 4 bits of that byte and lock them in as signature.
    header = bytearray(file_size_array + [0b10110000 | bit_depth] + [ord(x) for x in embed_filename[-3:]])
    print(list(header))
    encodable_bytes = header + embedded_bytes
    raw_image = img
    encoded_image = encode_into_image(bit_depth,encodable_bytes,img)
    print("done")
    savefilename = input("Please provide a filename, without extension\n")
    encoded_image.save(savefilename+".png",quality=100)
if mode.upper() == "D":
    image_filename = input("At the following prompt, choose the image you want to decode. {ENTER}")
    img = Image.open(choosefile([("Images", "*.png *.jpg"),]))
    #Header is 8 bytes long. At minimum bit depth, that's 64 bits across 64 pixels. So get the first 64 pixels to decode.
    header = find_header(img)
    byte_count = 0
    for i in range(4):
        byte_count*=256
        byte_count+=header[i]
    #Extract byte_count + header size bytes.
    file_payload_extracted = bytes(extract_bytes(byte_count+8,img,header[4]&0b1111))
    file_extension = "".join([chr(x) for x in header[-3:]])
    out_filename = "extracted." + file_extension
    with open(out_filename, mode= 'wb') as f:
        f.write(file_payload_extracted)
    print("Extracted file has been written to " + out_filename)
