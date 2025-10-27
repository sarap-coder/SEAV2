#ifndef RTT_TYPEKIT_CONFIG_H
#define RTT_TYPEKIT_CONFIG_H

#include "../rtt-config.h"

//
// See: <http://gcc.gnu.org/wiki/Visibility>
//
#define RTT_GCC_HASVISIBILITY
#if defined(__GNUG__) && defined(RTT_GCC_HASVISIBILITY) && (defined(__unix__) || defined(__APPLE__))

# if defined(RTT_TYPEKIT_DLL_EXPORT)
   // Use RTT_TYPEKIT_API for normal function exporting
#  define RTT_TYPEKIT_API    __attribute__((visibility("default")))

   // Use RTT_TYPEKIT_EXPORT for static template class member variables
   // They must always be 'globally' visible.
#  define RTT_TYPEKIT_EXPORT __attribute__((visibility("default")))

   // Use RTT_TYPEKIT_HIDE to explicitly hide a symbol
#  define RTT_TYPEKIT_HIDE   __attribute__((visibility("hidden")))
#  define RTT_TYPEKIT_EXT_TMPL extern
# else
#  define RTT_TYPEKIT_API
#  define RTT_TYPEKIT_EXPORT __attribute__((visibility("default")))
#  define RTT_TYPEKIT_HIDE   __attribute__((visibility("hidden")))
#  define RTT_TYPEKIT_EXT_TMPL extern
# endif
#else
   // NOT GNU
# if defined( __MINGW__ ) || defined( WIN32 )
#  if defined(RTT_TYPEKIT_DLL_EXPORT)
#   define RTT_TYPEKIT_API    __declspec(dllexport)
#   define RTT_TYPEKIT_EXPORT __declspec(dllexport)
#   define RTT_TYPEKIT_HIDE   
#   define RTT_TYPEKIT_EXT_TMPL extern
#  else
#   define RTT_TYPEKIT_API	 __declspec(dllimport)
#   define RTT_TYPEKIT_EXPORT __declspec(dllexport)
#   define RTT_TYPEKIT_HIDE 
#   define RTT_TYPEKIT_EXT_TMPL extern
#  endif
# else
#  define RTT_TYPEKIT_API
#  define RTT_TYPEKIT_EXPORT
#  define RTT_TYPEKIT_HIDE
#  define RTT_TYPEKIT_EXT_TMPL
# endif
#endif

#endif

