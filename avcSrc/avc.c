/*
    $Id: avc.c 87 2009-05-07 23:23:18Z marc.noirot $

    FLV Metadata updater

    Copyright (C) 2007, 2008, 2009 Marc Noirot <marc.noirot AT gmail.com>

    This file is part of FLVMeta.

    FLVMeta is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    FLVMeta is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with FLVMeta; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

/*
   This file is avc.c from FLVMeta 1.0.9, modified to have a main() that
   skips over FLV headers to find the first video keyframe and read the
   resolution from it.

   FLVMeta is available from http://code.google.com/p/flvmeta/

   Polsy, 15/09/2009
*/

#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>

#include "avc.h"

/**
    bit buffer handling
*/
typedef struct __bit_buffer {
    byte * start;
    size_t size;
    byte * current;
    uint8 read_bits;
} bit_buffer;

void skip_bits(bit_buffer * bb, size_t nbits) {
    bb->current = bb->current + ((nbits + bb->read_bits) / 8);
    bb->read_bits = (uint8)((bb->read_bits + nbits) % 8);
}

uint8 get_bit(bit_buffer * bb) {
    uint8 ret;
    ret = (*(bb->current) >> (7 - bb->read_bits)) & 0x1;
    if (bb->read_bits == 7) {
        bb->read_bits = 0;
        bb->current++;
    }
    else {
        bb->read_bits++;
    }
    return ret;
}

uint32 get_bits(bit_buffer * bb, size_t nbits) {
    uint32 i, ret;
    ret = 0;
    for (i = 0; i < nbits; i++) {
        ret = (ret << 1) + get_bit(bb);
    }
    return ret;
}

uint32 exp_golomb_ue(bit_buffer * bb) {
    uint8 bit, significant_bits;
    significant_bits = 0;
    bit = get_bit(bb);
    while (bit == 0) {
        significant_bits++;
        bit = get_bit(bb);
    }
    return (1 << significant_bits) + get_bits(bb, significant_bits) - 1;
}

sint32 exp_golomb_se(bit_buffer * bb) {
    sint32 ret;
    ret = exp_golomb_ue(bb);
    if ((ret & 0x1) == 0) {
        return -(ret >> 1);
    }
    else {
        return (ret + 1) >> 1;
    }
}

/* AVC type definitions */
#pragma pack(push, 1)

#define AVC_SEQUENCE_HEADER 0
#define AVC_NALU            1
#define AVC_END_OF_SEQUENCE 2

typedef struct __AVCDecoderConfigurationRecord {
    uint8 configurationVersion;
    uint8 AVCProfileIndication;
    uint8 profile_compatibility;
    uint8 AVCLevelIndication;
    uint8 lengthSizeMinusOne;
    uint8 numOfSequenceParameterSets;
} AVCDecoderConfigurationRecord;

#pragma pack(pop)

static void parse_scaling_list(uint32 size, bit_buffer * bb) {
    uint32 last_scale, next_scale, i;
    sint32 delta_scale;
    last_scale = 8;
    next_scale = 8;
    for (i = 0; i < size; i++) {
        if (next_scale != 0) {
            delta_scale = exp_golomb_se(bb);
            next_scale = (last_scale + delta_scale + 256) % 256;
        }
        if (next_scale != 0) {
            last_scale = next_scale;
        }
    }
}

/**
    Parses a SPS NALU to retrieve video width and height
*/
static void parse_sps(byte * sps, size_t sps_size, uint32 * width, uint32 * height) {
    bit_buffer bb;
    uint32 profile, pic_order_cnt_type, height_map;
    uint32 i, size;

    bb.start = sps;
    bb.size = sps_size;
    bb.current = sps;
    bb.read_bits = 0;

    /* skip first byte, since we already know we're parsing a SPS */
    skip_bits(&bb, 8);
    /* get profile */
    profile = get_bits(&bb, 8);
    /* skip 4 bits + 4 zeroed bits + 8 bits = 32 bits = 4 bytes */
    skip_bits(&bb, 16);

    /* read sps id, first exp-golomb encoded value */
    exp_golomb_ue(&bb);

    if (profile == 100 || profile == 110 || profile == 122 || profile == 144) {
        /* chroma format idx */
        if (exp_golomb_ue(&bb) == 3) {
            skip_bits(&bb, 1);
        }
        /* bit depth luma minus8 */
        exp_golomb_ue(&bb);
        /* bit depth chroma minus8 */
        exp_golomb_ue(&bb);
        /* Qpprime Y Zero Transform Bypass flag */
        skip_bits(&bb, 1);
        /* Seq Scaling Matrix Present Flag */
        if (get_bit(&bb)) {
            for (i = 0; i < 8; i++) {
                /* Seq Scaling List Present Flag */
                if (get_bit(&bb)) {
                    parse_scaling_list(i < 6 ? 16 : 64, &bb);
                }
            }
        }
    }
    /* log2_max_frame_num_minus4 */
    exp_golomb_ue(&bb);
    /* pic_order_cnt_type */
    pic_order_cnt_type = exp_golomb_ue(&bb);
    if (pic_order_cnt_type == 0) {
        /* log2_max_pic_order_cnt_lsb_minus4 */
        exp_golomb_ue(&bb);
    }
    else if (pic_order_cnt_type == 1) {
        /* delta_pic_order_always_zero_flag */
        skip_bits(&bb, 1);
        /* offset_for_non_ref_pic */
        exp_golomb_se(&bb);
        /* offset_for_top_to_bottom_field */
        exp_golomb_se(&bb);
        size = exp_golomb_ue(&bb);
        for (i = 0; i < size; i++) {
            /* offset_for_ref_frame */
            exp_golomb_se(&bb);
        }
    }
    /* num_ref_frames */
    exp_golomb_ue(&bb);
    /* gaps_in_frame_num_value_allowed_flag */
    skip_bits(&bb, 1);
    /* width */
    *width = (exp_golomb_ue(&bb) + 1) * 16;
    /* height */
    height_map = exp_golomb_ue(&bb) + 1;
    *height = (2 - get_bit(&bb)) * height_map * 16;
}

/**
    Tries to read the resolution of the current video packet.
    We assume to be at the first byte of the video data.
*/
size_t read_avc_resolution(FILE * f, uint32 * width, uint32 * height) {
    size_t bytes_read;
    byte avc_packet_type;
    uint24 composition_time;
    AVCDecoderConfigurationRecord adcr;
    uint16 sps_size;
    byte * sps_buffer;

    /* determine whether we're reading an AVCDecoderConfigurationRecord */
    bytes_read = fread(&avc_packet_type, 1, 1, f);
    if (bytes_read == 0 || avc_packet_type != AVC_SEQUENCE_HEADER) {
        return bytes_read;
    }

    /* read the composition time */
    if (fread(&composition_time, sizeof(uint24), 1, f) == 0) {
        return bytes_read;
    }
    bytes_read += sizeof(uint24);

    /* we need to read an AVCDecoderConfigurationRecord */
    if (fread(&adcr, sizeof(AVCDecoderConfigurationRecord), 1, f) == 0) {
        return bytes_read;
    }
    bytes_read += sizeof(AVCDecoderConfigurationRecord);

    /* number of SequenceParameterSets */
    if ((adcr.numOfSequenceParameterSets & 0x1F) == 0) {
        /* no SPS, return */
        return bytes_read;
    }

    /** read the first SequenceParameterSet found */
    /* SPS size */
    if (fread(&sps_size, sizeof(uint16), 1, f) == 0) {
        return bytes_read;
    }
    bytes_read += sizeof(uint16);
    sps_size = swap_uint16(sps_size);
    
    /* read the SPS entirely */
    sps_buffer = (byte *) malloc((size_t)sps_size);
    if (sps_buffer == NULL) {
        return bytes_read;
    }
    if (fread(sps_buffer, (size_t)sps_size, 1, f) == 0) {
        free(sps_buffer);
        return bytes_read;
    }
    bytes_read += (size_t)sps_size;

    /* parse SPS to determine video resolution */
    parse_sps(sps_buffer, (size_t)sps_size, width, height);
    
    free(sps_buffer);
    return bytes_read;
}

int main(int argc, char *argv[]) {
  uint w,h;
  FILE *f;
  size_t bread;
  char flvSig[2];
  unsigned int flags = 0;
  unsigned int tagType = 0;
  unsigned int isVideoTag = 0;
  unsigned int tagSz = 0;
  unsigned int vInfo = 0;

  if(argc != 2) {
    printf("No filename passed\n");
    return 1;
  }

  f = fopen(argv[1], "r");
  if(f == NULL) {
    printf("Failed to open file %s\n", argv[1]);
    return 1;
  }

  // FLV signature
  fread(flvSig, 1, 3, f);
  if(strncmp(flvSig, "FLV", 3)) {
    printf("Not an FLV file\n");
    return 1;
  }

  // skip 1 byte version
  fseek(f, 1, SEEK_CUR);
  fread(&flags, 1, 1, f);
  if(! (flags & 1)) {
    printf("Has no video data\n");
    return 1;
  }

  // skip 4-byte 'this header was X bytes' which is kinda too late to tell me now...
  fseek(f, 4, SEEK_CUR);

  while(! isVideoTag) {
    // previous tag size, not useful
    fseek(f, 4, SEEK_CUR);

    // tag type
    fread(&tagType, 1, 1, f);

    // I'd rather check this at the start of the loop, but apparently fseek clears EOF
    if(feof(f)) {
      printf("EOF reached\n");
      fclose(f);
      return 1;
    }

    // length of tag. In network order.
    tagSz = 0;
    fread(&tagSz, 1, 3, f);
    // flip it round
    tagSz = ntohl(tagSz);
    // shove it right
    tagSz = tagSz >> 8;

    // skip 4-byte timestamp
    fseek(f, 4, SEEK_CUR);
    // skip 3-byte stream ID which is zero anyway
    fseek(f, 3, SEEK_CUR);

    // So, did we want this data?
    if(tagType == 9) { // 9 = video
      isVideoTag = 1;
    } else { // anything else, don't care, skip it
      fseek(f, tagSz, SEEK_CUR);
    }
  }

  // First byte is the frame type. Must be a keyframe, it's the first one.
  fread(&vInfo, 1, 1, f);
  if((vInfo & 7) != 7) {
    switch(vInfo & 7) {
      case 2:
        printf("Not AVC FLV (H263 codec)\n"); break;
      case 3:
        printf("Not AVC FLV (screenvideo codec)\n"); break;
      case 4:
        printf("Not AVC FLV (VP6 codec)\n"); break;
      case 5:
        printf("Not AVC FLV (VP6 alpha codec)\n"); break;
      case 6:
        printf("Not AVC FLV (screenvideo v2 codec)\n"); break;
      default:
        printf("Not AVC FLV (codec %d)\n", (vInfo & 7)); break;
    }
    fclose(f);
    return 1;
  }

  bread = read_avc_resolution(f, &w, &h);
  fclose(f);

  printf("%dx%d\n", w, h);

  return 0;
}
