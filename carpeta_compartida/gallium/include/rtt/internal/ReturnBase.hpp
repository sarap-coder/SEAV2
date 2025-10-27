/***************************************************************************
  tag: The SourceWorks  Tue Sep 7 00:55:18 CEST 2010  ReturnBase.hpp

                        ReturnBase.hpp -  description
                           -------------------
    begin                : Tue September 07 2010
    copyright            : (C) 2010 The SourceWorks
    email                : peter@thesourceworks.com

 ***************************************************************************
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU General Public                   *
 *   License as published by the Free Software Foundation;                 *
 *   version 2 of the License.                                             *
 *                                                                         *
 *   As a special exception, you may use this file as part of a free       *
 *   software library without restriction.  Specifically, if other files   *
 *   instantiate templates or use macros or inline functions from this     *
 *   file, or you compile this file and link it with other files to        *
 *   produce an executable, this file does not by itself cause the         *
 *   resulting executable to be covered by the GNU General Public          *
 *   License.  This exception does not however invalidate any other        *
 *   reasons why the executable file might be covered by the GNU General   *
 *   Public License.                                                       *
 *                                                                         *
 *   This library is distributed in the hope that it will be useful,       *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU     *
 *   Lesser General Public License for more details.                       *
 *                                                                         *
 *   You should have received a copy of the GNU General Public             *
 *   License along with this library; if not, write to the Free Software   *
 *   Foundation, Inc., 59 Temple Place,                                    *
 *   Suite 330, Boston, MA  02111-1307  USA                                *
 *                                                                         *
 ***************************************************************************/


#ifndef ORO_RETURN_BASE_HPP
#define ORO_RETURN_BASE_HPP

#include <boost/type_traits.hpp>

namespace RTT
{
    namespace internal
    {
        /**
         * Implementation of ret() which takes the same signature
         * as call().
         */
        template<int, class F>
        struct ReturnBaseImpl;

        /**
         * This is the base class that defines the interface
         * of returning data from method invocations.
         */
        template<class F>
        struct ReturnBase
            : public ReturnBaseImpl<boost::function_traits<F>::arity, F>
        {};


        template<class F>
        struct ReturnBaseImpl<0,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<1,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<2,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<3,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            typedef typename boost::function_traits<F>::arg3_type arg3_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2, arg3_type a3) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<4,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            typedef typename boost::function_traits<F>::arg3_type arg3_type;
            typedef typename boost::function_traits<F>::arg4_type arg4_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2, arg3_type a3, arg4_type a4) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<5,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            typedef typename boost::function_traits<F>::arg3_type arg3_type;
            typedef typename boost::function_traits<F>::arg4_type arg4_type;
            typedef typename boost::function_traits<F>::arg5_type arg5_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2, arg3_type a3, arg4_type a4, arg5_type a5) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<6,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            typedef typename boost::function_traits<F>::arg3_type arg3_type;
            typedef typename boost::function_traits<F>::arg4_type arg4_type;
            typedef typename boost::function_traits<F>::arg5_type arg5_type;
            typedef typename boost::function_traits<F>::arg6_type arg6_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2, arg3_type a3, arg4_type a4, arg5_type a5, arg6_type a6) = 0;
            virtual result_type ret() = 0;
        };

        template<class F>
        struct ReturnBaseImpl<7,F>
        {
            typedef typename boost::function_traits<F>::result_type result_type;
            typedef typename boost::function_traits<F>::arg1_type arg1_type;
            typedef typename boost::function_traits<F>::arg2_type arg2_type;
            typedef typename boost::function_traits<F>::arg3_type arg3_type;
            typedef typename boost::function_traits<F>::arg4_type arg4_type;
            typedef typename boost::function_traits<F>::arg5_type arg5_type;
            typedef typename boost::function_traits<F>::arg6_type arg6_type;
            typedef typename boost::function_traits<F>::arg7_type arg7_type;
            virtual ~ReturnBaseImpl() {}

            virtual result_type ret(arg1_type a1, arg2_type a2, arg3_type a3, arg4_type a4, arg5_type a5, arg6_type a6, arg7_type a7) = 0;
            virtual result_type ret() = 0;
        };
    }
}
#endif
