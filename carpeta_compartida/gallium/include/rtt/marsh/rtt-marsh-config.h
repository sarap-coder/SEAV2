#ifndef RTT_MARSH_CONFIG_H
#define RTT_MARSH_CONFIG_H

#include "../rtt-config.h"

//
// See: <http://gcc.gnu.org/wiki/Visibility>
//
#define RTT_GCC_HASVISIBILITY
#if defined(__GNUG__) && defined(RTT_GCC_HASVISIBILITY) && (defined(__unix__) || defined(__APPLE__))

# if defined(RTT_MARSH_DLL_EXPORT)
   // Use RTT_MARSH_API for normal function exporting
#  define RTT_MARSH_API    __attribute__((visibility("default")))

   // Use RTT_MARSH_EXPORT for static template class member variables
   // They must always be 'globally' visible.
#  define RTT_MARSH_EXPORT __attribute__((visibility("default")))

   // Use RTT_MARSH_HIDE to explicitly hide a symbol
#  define RTT_MARSH_HIDE   __attribute__((visibility("hidden")))

# else
#  define RTT_MARSH_API
#  define RTT_MARSH_EXPORT __attribute__((visibility("default")))
#  define RTT_MARSH_HIDE   __attribute__((visibility("hidden")))
# endif
#else
   // NOT GNU
# if defined( __MINGW__ ) || defined( WIN32 )
#  if defined(RTT_MARSH_DLL_EXPORT)
#   define RTT_MARSH_API    __declspec(dllexport)
#   define RTT_MARSH_EXPORT __declspec(dllexport)
#   define RTT_MARSH_HIDE   
#  else
#   define RTT_MARSH_API    __declspec(dllimport)
#   define RTT_MARSH_EXPORT __declspec(dllexport)
#   define RTT_MARSH_HIDE 
#  endif
# else
#  define RTT_MARSH_API
#  define RTT_MARSH_EXPORT
#  define RTT_MARSH_HIDE
# endif
#endif

#endif

