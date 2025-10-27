#ifndef ORO_RTT_types_FWD_HPP
#define ORO_RTT_types_FWD_HPP

namespace RTT {
    namespace types {
        class BinaryOp;
        class EmptyTypeInfo;
        class GlobalsRepository;
        class OperatorRepository;
        class TransportPlugin;
        class TypeInfo;
        class TypeInfoGenerator;
        class TypeInfoRepository;
        class TypeMarshaller;
        class TypeTransporter;
        class TypekitPlugin;
        class TypekitRepository;
        class UnaryOp;
        struct TypeConstructor;
        template <typename T, bool has_ostream>
        struct StdVectorTemplateTypeInfo;
        template<class S>
        struct TemplateConstructor;
        template<class T>
        struct EnumTypeInfo;
        template<typename T, bool has_ostream>
        class BoostArrayTypeInfo;
        template<typename T, bool has_ostream>
        class CArrayTypeInfo;
        template<typename T, bool has_ostream>
        class SequenceTypeInfo;
        template<typename T, bool has_ostream>
        class StructTypeInfo;
        template<typename T, bool use_ostream>
        class TemplateTypeInfo;
        template<typename T>
        struct StdVectorBuilder;
        template<typename T>
        struct TypeInfoName;
        template<typename function>
        class BinaryOperator;
        template<typename function>
        class UnaryOperator;
    }
    namespace detail {
        using namespace types;
    }
}
#endif
