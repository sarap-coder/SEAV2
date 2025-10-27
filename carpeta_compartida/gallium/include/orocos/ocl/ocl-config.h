#ifndef OCL_CONFIG_H
#define OCL_CONFIG_H

#define OCL_VERSION       2.9.0
#define OCL_VERSION_MAJOR 2
#define OCL_VERSION_MINOR 9
#define OCL_VERSION_PATCH 0

#include <rtt/rtt-config.h>

#if defined(__GNUG__) && (defined(__unix__) || defined(__APPLE__))

# if defined(OCL_DLL_EXPORT)
   // Use OCL_API for normal function exporting
#  define OCL_API    __attribute__((visibility("default")))

   // Use OCL_EXPORT for static template class member variables
   // They must always be 'globally' visible.
#  define OCL_EXPORT __attribute__((visibility("default")))

   // Use OCL_HIDE to explicitly hide a symbol
#  define OCL_HIDE   __attribute__((visibility("hidden")))

# else
#  define OCL_API
#  define OCL_EXPORT __attribute__((visibility("default")))
#  define OCL_HIDE   __attribute__((visibility("hidden")))
# endif
#else
   // Win32 and NOT GNU
# if defined( WIN32 ) && !defined ( __MINGW32__ )
#  if defined(OCL_DLL_EXPORT)
#   define OCL_API    __declspec(dllexport)
#   define OCL_EXPORT __declspec(dllexport)
#   define OCL_HIDE   
#  else
#   define OCL_API	 __declspec(dllimport)
#   define OCL_EXPORT __declspec(dllexport)
#   define OCL_HIDE 
#  endif
# else
#  define OCL_API
#  define OCL_EXPORT
#  define OCL_HIDE
# endif
#endif

#endif // OCL_CONFIG_H
