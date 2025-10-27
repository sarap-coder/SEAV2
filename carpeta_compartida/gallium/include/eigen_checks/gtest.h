/*
 * Copyright 2019 PAL Robotics SL. All Rights Reserved
 *
 * Unauthorized copying of this file, via any medium is strictly prohibited,
 * unless it was supplied under the terms of a license agreement or
 * nondisclosure agreement with PAL Robotics SL. In this case it may not be
 * copied or disclosed except in accordance with the terms of that agreement.
 */
#ifndef EIGEN_CHECKS_GTEST_H_
#define EIGEN_CHECKS_GTEST_H_
#include <limits>
#include <type_traits>

#include <eigen_checks/gtest-equal.h>
#include <eigen_checks/gtest-equal_sparse.h>

#define EIGEN_MATRIX_EQUAL(MatrixA, MatrixB)                                             \
  eigen_checks::internal::MatricesNear(                                                  \
      MatrixA, #MatrixA, MatrixB, #MatrixB,                                              \
      static_cast<typename std::remove_reference<decltype(MatrixA)>::type::Scalar>(0.0), "0.0")

#define EIGEN_MATRIX_EQUAL_DOUBLE(MatrixA, MatrixB)                                      \
  eigen_checks::internal::MatricesNear(                                                  \
      MatrixA, #MatrixA, MatrixB, #MatrixB,                                              \
      static_cast<typename std::remove_reference<decltype(MatrixA)>::type::Scalar>(      \
          eigen_checks::internal::kDefaultPrecision),                                    \
      "Floating point precision")

#define EIGEN_MATRIX_NEAR(MatrixA, MatrixB, Precision)                                   \
  eigen_checks::internal::MatricesNear(MatrixA, #MatrixA, MatrixB, #MatrixB, Precision, #Precision)

#define EIGEN_MATRIX_ZERO(MatrixA, Precision)                                            \
  eigen_checks::internal::MatrixZero(MatrixA, #MatrixA, Precision, #Precision)

#endif  // EIGEN_CHECKS_GTEST_H_
