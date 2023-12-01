/*=========================================================================

  Program: GDCM (Grassroots DICOM). A DICOM library

  Copyright (c) 2006-2011 Mathieu Malaterre
  All rights reserved.
  See Copyright.txt or http://gdcm.sourceforge.net/Copyright.html for details.

     This software is distributed WITHOUT ANY WARRANTY; without even
     the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
     PURPOSE.  See the above copyright notice for more information.

=========================================================================*/
/*
 * This example is ... guess what this is for :)
 */

#include "gdcmReader.h"
#include "gdcmUIDGenerator.h"
#include "gdcmWriter.h"
#include "gdcmAttribute.h"

#include <iostream>

#ifdef GDCM_USE_SYSTEM_OPENSSL
#include "gdcmCryptoFactory.h"
void test_openssl_link()
{
  (void)gdcm::CryptoFactory::GetFactoryInstance(gdcm::CryptoFactory::OPENSSL);
}
#endif

#ifdef GDCM_USE_SYSTEM_JSON
#include "gdcmJSON.h"
void test_json_link()
{
  gdcm::JSON json;
  json.PrettyPrintOn();
}
#endif

bool test_uid()
{
  gdcm::UIDGenerator uid;
  uid.SetRoot( "1.2.3.4.0.0.1" );
  const char *s = uid.Generate();
  return gdcm::UIDGenerator::IsValid(s);
}

int main(int argc, char* argv[])
{
  if (argc < 3)
  {
    std::cerr << argv[0] << " input.dcm output.dcm" << std::endl;
    return 1;
  }
  const char* filename = argv[1];
  const char* outfilename = argv[2];

  // Instantiate the reader:
  gdcm::Reader reader;
  reader.SetFileName(filename);
  if (!reader.Read())
  {
    std::cerr << "Could not read: " << filename << std::endl;
    return 1;
  }

  // If we reach here, we know for sure only 1 thing:
  // It is a valid DICOM file (potentially an old ACR-NEMA 1.0/2.0 file)
  // (Maybe, it's NOT a Dicom image -could be a DICOMDIR, a RTSTRUCT, etc-)

  // The output of gdcm::Reader is a gdcm::File
  gdcm::File& file = reader.GetFile();

  // the dataset is the the set of element we are interested in:
  gdcm::DataSet& ds = file.GetDataSet();

  // Construct a static(*) type for Image Comments :
  gdcm::Attribute<0x0020, 0x4000> imagecomments;
  imagecomments.SetValue("Hello, World !");

  // Now replace the Image Comments from the dataset with our:
  ds.Replace(imagecomments.GetAsDataElement());

  // Write the modified DataSet back to disk
  gdcm::Writer writer;
  writer.CheckFileMetaInformationOff(); // Do not attempt to reconstruct the file meta to preserve the file
                                        // as close to the original as possible.
  writer.SetFileName(outfilename);
  writer.SetFile(file);
  if (!writer.Write())
  {
    std::cerr << "Could not write: " << outfilename << std::endl;
    return 1;
  }
  std::cout << "GDCM test: success\n";
  return 0;
}

/*
 * (*) static type, means that extra DICOM information VR & VM are computed at compilation time.
 * The compiler is deducing those values from the template arguments of the class.
 */
