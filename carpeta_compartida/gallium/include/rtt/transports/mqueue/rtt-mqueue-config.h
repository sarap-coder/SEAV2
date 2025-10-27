#ifndef RTT_MQUEUE_CONFIG_H
#define RTT_MQUEUE_CONFIG_H

//
// See: <http://gcc.gnu.org/wiki/Visibility>
//
#define RTT_GCC_HASVISIBILITY
#if defined(__GNUG__) && defined(RTT_GCC_HASVISIBILITY) && (defined(__unix__) || defined(__APPLE__))

# if defined(RTT_MQUEUE_DLL_EXPORT)
   // Use RTT_MQUEUE_API for normal function exporting
#  define RTT_MQUEUE_API    __attribute__((visibility("default")))

   // Use RTT_MQUEUE_EXPORT for static template class member variables
   // They must always be 'globally' visible.
#  define RTT_MQUEUE_EXPORT __attribute__((visibility("default")))

   // Use RTT_MQUEUE_HIDE to explicitly hide a symbol
#  define RTT_MQUEUE_HIDE   __attribute__((visibility("hidden")))

# else
#  define RTT_MQUEUE_API
#  define RTT_MQUEUE_EXPORT __attribute__((visibility("default")))
#  define RTT_MQUEUE_HIDE   __attribute__((visibility("hidden")))
# endif
#else
   // NOT GNU
# if defined( __MINGW__ ) || defined( WIN32 )
#  if defined(RTT_MQUEUE_DLL_EXPORT)
#   define RTT_MQUEUE_API    __declspec(dllexport)
#   define RTT_MQUEUE_EXPORT __declspec(dllexport)
#   define RTT_MQUEUE_HIDE   
#  else
#   define RTT_MQUEUE_API	 __declspec(dllimport)
#   define RTT_MQUEUE_EXPORT __declspec(dllexport)
#   define RTT_MQUEUE_HIDE 
#  endif
# else
#  define RTT_MQUEUE_API
#  define RTT_MQUEUE_EXPORT
#  define RTT_MQUEUE_HIDE
# endif
#endif

#endif

